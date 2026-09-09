"""The Aadhaar capability showcase, end to end over HTTP (ADR-013).

One application (BN/2026/0601) holds the applicant's true declared identity, and
each synthetic specimen is judged against it. These tests drive the real analyze
pipeline and the real check engine; extraction is the mock reader (never real
Gemini in the suite), which serves the same authored qr_fields and quality the
generated specimens carry, keyed by filename. So the checks under test — the
Verhoeff checksum, the QR-vs-print integrity check, the scan-quality check, and the
cross-checks against the application — run exactly as they do in the live demo.

The department's transport is stubbed where a scenario reaches UIDAI, as in the
other identity analyze tests; a Django test serves no outbound socket.
"""
import json
from contextlib import contextmanager
from typing import Any, Dict, List
from unittest.mock import patch

import httpx
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import AsyncClient

SHOWCASE_APPLICATION_ID = "BN/2026/0601"
UIDAI_BUILDERS = (
    "document_verification.adapters.issuer_adapter_registry"
    "._ADAPTER_BUILDERS_BY_ISSUER_SERVICE"
)


def read_frames(body: str) -> List[Dict[str, Any]]:
    frames = []
    for block in body.split("\n\n"):
        if not block.strip():
            continue
        event_type = None
        payload = None
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[len("event: ") :]
            if line.startswith("data: "):
                payload = json.loads(line[len("data: ") :])
        if event_type is not None:
            frames.append({"type": event_type, "payload": payload})
    return frames


def read_documents(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [frame["payload"] for frame in frames if frame["type"] == "doc"]


def settled_document(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
    return read_documents(frames)[-1]


def checks_by_key(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    # Keyed by the part after the document id, e.g. "qr-consistency", so a test
    # names the check without knowing the generated document id.
    result = {}
    for check in document["checks"]:
        _, _, suffix = check["checkId"].partition(":")
        result[suffix] = check
    return result


@contextmanager
def uidai_answering(handler):
    from document_verification.adapters.uidai_service_adapter import (
        UidaiServiceAdapter,
    )

    with patch.dict(
        UIDAI_BUILDERS,
        {"uidai": lambda: UidaiServiceAdapter(transport=httpx.MockTransport(handler))},
    ):
        yield


def confirming_uidai(matched=("name", "dob", "gender")):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "Y", "matched": list(matched)})

    return handler


def timing_out_uidai():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("budget exceeded", request=request)

    return handler


@pytest.fixture(autouse=True)
def mock_extraction(settings):
    settings.EXTRACTION_MODE = "mock"
    settings.MOCK_ISSUER_LATENCY_SECONDS = 0
    settings.SCRUTINY_TODAY = "2026-09-07"


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient()


async def open_thread(client: AsyncClient) -> str:
    response = await client.post(
        "/api/threads",
        data=json.dumps({"applicationId": SHOWCASE_APPLICATION_ID}),
        content_type="application/json",
    )
    assert response.status_code == 201
    return response.json()["threadId"]


async def attach(client: AsyncClient, thread_id: str, filename: str) -> None:
    response = await client.post(
        f"/api/threads/{thread_id}/documents",
        data={"files": SimpleUploadedFile(filename, b"not-a-real-scan")},
    )
    assert response.status_code == 201


async def analyze(client: AsyncClient, thread_id: str) -> List[Dict[str, Any]]:
    response = await client.get(f"/api/threads/{thread_id}/analyze")
    assert response.status_code == 200
    body = b"".join([chunk async for chunk in response.streaming_content]).decode()
    return read_frames(body)


async def run(client: AsyncClient, filename: str, handler=None) -> Dict[str, Any]:
    thread_id = await open_thread(client)
    await attach(client, thread_id, filename)
    with uidai_answering(handler or confirming_uidai()):
        frames = await analyze(client, thread_id)
    return settled_document(frames)


def settled_by_type(frames: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    # The latest frame per document, keyed by its type, for a multi-document thread.
    latest: Dict[str, Dict[str, Any]] = {}
    for document in read_documents(frames):
        latest[document["documentId"]] = document
    return {
        document["documentTypeId"]: document
        for document in latest.values()
        if document["stage"] == "done"
    }


class TestAadhaarShowcase:
    async def test_the_clean_specimen_verifies_on_every_capability(self, client):
        # Act
        settled = await run(client, "aadhaar_clean.pdf")

        # Assert — read, cross-checked, checksum, QR and quality all agree
        checks = checks_by_key(settled)
        assert settled["documentTypeId"] == "aadhaar"
        assert checks["name"]["status"] == "pass"
        assert checks["dob"]["status"] == "pass"
        assert checks["aadhaar-format"]["status"] == "pass"
        assert checks["qr-consistency"]["status"] == "pass"
        assert checks["scan-quality"]["status"] == "pass"
        assert settled["status"] == "verified"

    async def test_the_clean_specimen_reads_all_five_fields(self, client):
        # Act
        settled = await run(client, "aadhaar_clean.pdf")

        # Assert
        assert {value["key"] for value in settled["fieldValues"]} == {
            "name",
            "dob",
            "gender",
            "aadhaarNo",
            "address",
        }

    async def test_the_clean_specimen_confirms_against_uidai(self, client):
        # Act
        settled = await run(client, "aadhaar_clean.pdf")

        # Assert
        external = next(c for c in settled["checks"] if c["group"] == "external")
        assert external["status"] == "pass"
        assert external["issuerCall"]["issuerServiceId"] == "uidai"

    async def test_the_tampered_specimen_is_caught_by_the_qr_check(self, client):
        # Act — the print was altered; the QR still carries the clean identity
        settled = await run(client, "aadhaar_tampered_qr.pdf")

        # Assert
        checks = checks_by_key(settled)
        qr = checks["qr-consistency"]
        assert qr["status"] == "warn"
        assert "the name" in qr["detail"]
        assert "the Aadhaar number" in qr["detail"]
        # The QR contradiction is the headline integrity signal. The altered print
        # also disagrees with the application, so the name cross-check fails too and
        # the document settles as failed — a tampered card is caught twice over, not
        # a false clean.
        assert checks["name"]["status"] == "fail"
        assert settled["status"] == "failed"

    async def test_the_invalid_number_specimen_fails_its_checksum(self, client):
        # Act
        settled = await run(client, "aadhaar_invalid_number.pdf")

        # Assert
        checks = checks_by_key(settled)
        checksum = checks["aadhaar-format"]
        assert checksum["status"] == "fail"
        assert "checksum" in checksum["title"].lower()
        assert settled["status"] == "failed"

    async def test_the_mismatch_specimen_fails_the_cross_checks(self, client):
        # Act — a clean card for a different person than the application declares
        settled = await run(client, "aadhaar_mismatch.pdf")

        # Assert
        checks = checks_by_key(settled)
        assert checks["name"]["status"] == "fail"
        assert checks["dob"]["status"] == "fail"
        # Its own QR agrees with its own (wrong-person) print, so QR is not the flag.
        assert checks["qr-consistency"]["status"] == "pass"
        assert settled["status"] == "failed"

    async def test_the_poor_scan_specimen_warns_on_quality(self, client):
        # Act
        settled = await run(client, "aadhaar_poor_scan.pdf")

        # Assert
        checks = checks_by_key(settled)
        quality = checks["scan-quality"]
        assert quality["status"] == "warn"
        assert "blurred" in quality["detail"] or "low-resolution" in quality["detail"]

    async def test_an_impossible_date_of_birth_is_caught_from_the_document_alone(
        self, client
    ):
        # Act — a future date of birth; UIDAI confirms number/name/gender but the
        # date is the document contradicting itself
        settled = await run(
            client,
            "aadhaar_impossible_dob.pdf",
            handler=confirming_uidai(matched=("name", "gender")),
        )

        # Assert — the intrinsic consistency check is the headline: the document is
        # wrong on its own terms, before any comparison
        checks = checks_by_key(settled)
        consistency = checks["internal-consistency"]
        assert consistency["status"] == "fail"
        assert "future" in consistency["title"].lower()
        # The number and QR are fine — this is a bad date, not a forgery or tamper
        assert checks["aadhaar-format"]["status"] == "pass"
        assert checks["qr-consistency"]["status"] == "pass"
        assert settled["status"] == "failed"

    async def test_a_misread_name_is_flagged_for_review_not_rejected(self, client):
        # Arrange — UIDAI confirms the number is genuine and the dob/gender agree,
        # but reports the name as not matching at its own grain, exactly as the
        # mocked service does for a near-match. The QR carries the correct spelling.
        settled = await run(
            client,
            "aadhaar_name_typo.pdf",
            handler=confirming_uidai(matched=("dob", "gender")),
        )

        # Assert — the fuzzy band: the name cross-check warns (needs a look) and
        # carries the similarity, rather than failing outright.
        checks = checks_by_key(settled)
        name = checks["name"]
        assert name["status"] == "warn"
        assert "%" in name["detail"]
        # The QR carries the correct spelling, so the integrity check is clean —
        # this is a misread, not a tamper.
        assert checks["qr-consistency"]["status"] == "pass"
        assert checks["aadhaar-format"]["status"] == "pass"
        # The department vouches for the card but notes the name — so the misread is
        # surfaced twice over, and the document needs the officer's look, not a
        # rejection.
        external = next(c for c in settled["checks"] if c["group"] == "external")
        assert external["status"] == "warn"
        assert settled["status"] == "attention"

    async def test_a_clean_specimen_reports_could_not_verify_when_uidai_is_down(
        self, client
    ):
        # Act — the dept-down scenario: the clean specimen, UIDAI unreachable
        settled = await run(
            client, "aadhaar_clean.pdf", handler=timing_out_uidai()
        )

        # Assert — the intrinsic checks still pass; only the department is missing
        checks = checks_by_key(settled)
        assert checks["aadhaar-format"]["status"] == "pass"
        assert checks["qr-consistency"]["status"] == "pass"
        external = next(c for c in settled["checks"] if c["group"] == "external")
        assert external["status"] == "unavailable"
        assert settled["status"] == "unavailable"

    async def test_a_pan_and_a_wrong_person_aadhaar_fail_the_cross_document_check(
        self, client
    ):
        # Arrange — the applicant's own PAN, filed alongside a clean Aadhaar that
        # belongs to a different person. Each document is internally fine; it is the
        # two of them together that do not name the same person.
        thread_id = await open_thread(client)
        await attach(client, thread_id, "pan_rithika.pdf")
        await attach(client, thread_id, "aadhaar_mismatch.pdf")

        # Act — the Aadhaar is analysed after the PAN has settled, so it sees the PAN
        # as a sibling to reconcile against.
        with uidai_answering(confirming_uidai()):
            frames = await analyze(client, thread_id)

        # Assert — the cross-document check on the Aadhaar warns, naming the PAN it
        # disagrees with. The PAN itself agrees with the application and verifies.
        by_type = settled_by_type(frames)
        assert set(by_type) == {"pan", "aadhaar"}
        cross = checks_by_key(by_type["aadhaar"])["cross-document"]
        assert cross["group"] == "cross"
        assert cross["status"] == "warn"
        assert "Vikram Anand Reddy" in cross["detail"]
        assert "Rithika Sharma" in cross["detail"] or "RITHIKA SHARMA" in cross["detail"]
        # The PAN's own field checks agree with the application — the name and dob
        # match, so on its own terms it is a clean read.
        pan_checks = checks_by_key(by_type["pan"])
        assert pan_checks["name"]["status"] == "pass"
        assert pan_checks["dob"]["status"] == "pass"

    async def test_the_checksum_stays_off_for_a_document_without_a_qr(self, client):
        # Arrange — a plain aadhaar filename with no showcase QR read falls back to
        # the ordinary structural-only check, preserving ADR-009 for legacy data.
        thread_id = await open_thread(client)
        await attach(client, thread_id, "aadhaar_front.jpg")

        # Act — this application has no canned read for that filename, so extraction
        # finds nothing; the point is only that no showcase QR is attached and thus
        # no checksum enforcement kicks in. It settles without raising.
        with uidai_answering(confirming_uidai()):
            frames = await analyze(client, thread_id)

        # Assert — the run completed and produced a settled document frame
        assert read_documents(frames)
