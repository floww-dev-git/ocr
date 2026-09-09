"""The five land / revenue documents end to end over HTTP.

EC, land conversion certificate, market value certificate, pattadar pass book and
ORC are all manual-only: no issuing department publishes a verification interface,
so each settles through the same `ManualVerificationCheck` path the Irrigation NOC
introduced. These tests assert that no department is ever called, that the officer
is told so, that the seeded pattadar-vs-application extent discrepancy is caught,
and that a manual-only document sits correctly on a thread beside a PAN that does
call a department.
"""
import json
from contextlib import contextmanager
from typing import Any, Dict, List
from unittest.mock import patch

import httpx
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import AsyncClient

MISMATCH_APPLICATION_ID = "BN/2026/0377"
ADAPTER_BUILDERS = (
    "document_verification.adapters.issuer_adapter_registry"
    "._ADAPTER_BUILDERS_BY_ISSUER_SERVICE"
)

# (filename, document_type_id, label) for each manual-only land document.
LAND_DOCUMENTS = [
    ("encumbrance_certificate.pdf", "ec", "Encumbrance certificate"),
    ("land_conversion_certificate.pdf", "conversion_cert", "Land conversion certificate"),
    ("market_value_certificate.pdf", "market_value_cert", "Market value certificate"),
    ("pattadar_passbook.pdf", "pattadar_passbook", "Pattadar pass book / Title deed"),
    ("occupancy_rights_certificate.pdf", "orc", "Occupancy rights certificate"),
]


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


def checks_by_id(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {check["checkId"]: check for check in document["checks"]}


def issuer_check(document: Dict[str, Any]) -> Dict[str, Any]:
    return next(check for check in document["checks"] if check["group"] == "external")


def read_summary(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
    return next(frame["payload"] for frame in frames if frame["type"] == "summary")


@contextmanager
def no_department_reachable():
    """Every issuer adapter removed, so any outbound call would fail loudly.

    None of these five documents needs one; wrapping the run in this turns the
    absence of a call into an assertion rather than an assumption.
    """
    with patch.dict(ADAPTER_BUILDERS, {}, clear=True):
        yield


@contextmanager
def itd_answering(handler):
    from document_verification.adapters.itd_pan_service_adapter import (
        ItdPanServiceAdapter,
    )

    with patch.dict(
        ADAPTER_BUILDERS,
        {
            "itd_pan": lambda: ItdPanServiceAdapter(
                transport=httpx.MockTransport(handler)
            )
        },
    ):
        yield


def valid_pan(request: httpx.Request) -> httpx.Response:
    # The seeded PAN for BN/2026/0377 (the application the land documents sit on).
    return httpx.Response(
        200,
        json={
            "pan": "BNMPS7720K",
            "status": "VALID",
            "nameMatch": True,
            "dobMatch": True,
        },
    )


@pytest.fixture(autouse=True)
def mock_extraction(settings):
    settings.EXTRACTION_MODE = "mock"
    settings.MOCK_ISSUER_LATENCY_SECONDS = 0
    settings.SCRUTINY_TODAY = "2026-09-07"


@pytest.fixture
def client() -> AsyncClient:
    return AsyncClient()


async def open_thread(client: AsyncClient, application_id: str) -> str:
    response = await client.post(
        "/api/threads",
        data=json.dumps({"applicationId": application_id}),
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


async def run_one(
    client: AsyncClient, application_id: str, filename: str
) -> List[Dict[str, Any]]:
    thread_id = await open_thread(client, application_id)
    await attach(client, thread_id, filename)
    with no_department_reachable():
        return await analyze(client, thread_id)


class TestLandDocumentsAnalyze:
    @pytest.mark.parametrize("filename, type_id, label", LAND_DOCUMENTS)
    async def test_each_land_document_is_identified_read_and_settled_by_hand(
        self, client, filename, type_id, label
    ):
        # Arrange & Act
        frames = await run_one(client, MISMATCH_APPLICATION_ID, filename)

        # Assert
        settled = settled_document(frames)
        assert settled["documentTypeId"] == type_id
        assert settled["documentTypeLabel"] == label
        assert settled["implemented"] is True
        assert settled["stage"] == "done"
        issuer = issuer_check(settled)
        assert issuer["status"] == "info"
        assert issuer["title"] == f"No department interface for this {label}"
        assert issuer["issuerCall"] is None

    @pytest.mark.parametrize("filename, type_id, label", LAND_DOCUMENTS)
    async def test_no_department_is_ever_called(self, client, filename, type_id, label):
        # Arrange & Act — no_department_reachable() would raise on any outbound call
        frames = await run_one(client, MISMATCH_APPLICATION_ID, filename)

        # Assert
        settled = settled_document(frames)
        assert issuer_check(settled)["issuerCall"] is None

    async def test_the_clean_documents_leave_the_thread_clear(self, client):
        # Arrange & Act — EC on the seeded application reads consistent with the form
        frames = await run_one(
            client, MISMATCH_APPLICATION_ID, "encumbrance_certificate.pdf"
        )

        # Assert
        settled = settled_document(frames)
        assert settled["status"] == "verified"
        summary = read_summary(frames)
        assert summary["threadStatus"] == "clear"
        assert summary["openItems"] == []

    async def test_the_encumbrance_certificate_compares_owner_and_survey(self, client):
        # Arrange & Act
        frames = await run_one(
            client, MISMATCH_APPLICATION_ID, "encumbrance_certificate.pdf"
        )

        # Assert
        settled = settled_document(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        assert checks[f"{document_id}:name"]["status"] == "pass"
        assert checks[f"{document_id}:name"]["fieldKey"] == "owner"
        assert checks[f"{document_id}:survey"]["status"] == "pass"

    async def test_the_conversion_certificate_compares_all_four_fields(self, client):
        # Arrange & Act
        frames = await run_one(
            client, MISMATCH_APPLICATION_ID, "land_conversion_certificate.pdf"
        )

        # Assert — applicant, survey, village and extent all agree
        settled = settled_document(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        assert checks[f"{document_id}:name"]["status"] == "pass"
        assert checks[f"{document_id}:survey"]["status"] == "pass"
        assert checks[f"{document_id}:village"]["status"] == "pass"
        assert checks[f"{document_id}:extent"]["status"] == "pass"

    async def test_the_market_value_certificate_does_not_check_the_rate(self, client):
        # Arrange & Act — the rate has no counterpart on the application form
        frames = await run_one(
            client, MISMATCH_APPLICATION_ID, "market_value_certificate.pdf"
        )

        # Assert
        settled = settled_document(frames)
        read_values = {value["key"]: value["value"] for value in settled["fieldValues"]}
        assert read_values["marketValuePerSqYd"] == "Rs. 45,000 per sq. yd"
        assert not [
            check
            for check in settled["checks"]
            if check["fieldKey"] == "marketValuePerSqYd"
        ]
        # But the parcel it names is still compared.
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        assert checks[f"{document_id}:survey"]["status"] == "pass"
        assert checks[f"{document_id}:village"]["status"] == "pass"

    async def test_the_pattadar_passbook_extent_discrepancy_warns(self, client):
        # Arrange & Act — the revenue record reads 390 sq. yd, the application 420
        frames = await run_one(
            client, MISMATCH_APPLICATION_ID, "pattadar_passbook.pdf"
        )

        # Assert
        settled = settled_document(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        extent_check = checks[f"{document_id}:extent"]
        assert extent_check["status"] == "warn"
        assert "390" in extent_check["detail"]
        assert "420" in extent_check["detail"]
        # A discrepancy the officer can explain leaves the thread needing a look,
        # not failed.
        assert settled["status"] == "attention"
        summary = read_summary(frames)
        assert summary["threadStatus"] == "attention"
        assert any(
            item["checkId"] == f"{document_id}:extent" for item in summary["openItems"]
        )

    async def test_the_pattadar_name_and_survey_still_agree_alongside_the_warning(
        self, client
    ):
        # Arrange & Act — one warning field must not drag the others with it
        frames = await run_one(
            client, MISMATCH_APPLICATION_ID, "pattadar_passbook.pdf"
        )

        # Assert
        settled = settled_document(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        assert checks[f"{document_id}:name"]["status"] == "pass"
        assert checks[f"{document_id}:survey"]["status"] == "pass"

    async def test_the_pattadar_reports_its_three_structure_elements(self, client):
        # Arrange & Act
        frames = await run_one(
            client, MISMATCH_APPLICATION_ID, "pattadar_passbook.pdf"
        )

        # Assert
        settled = settled_document(frames)
        assert settled["structureFindings"] == {
            "photo": True,
            "seal": True,
            "signature": True,
        }
        structure_checks = [
            check for check in settled["checks"] if check["group"] == "structure"
        ]
        assert len(structure_checks) == 3

    async def test_asking_the_department_again_is_refused_for_a_land_document(
        self, client
    ):
        # Arrange
        thread_id = await open_thread(client, MISMATCH_APPLICATION_ID)
        await attach(client, thread_id, "occupancy_rights_certificate.pdf")
        with no_department_reachable():
            frames = await analyze(client, thread_id)
        document_id = settled_document(frames)["documentId"]

        # Act
        response = await client.post(
            f"/api/threads/{thread_id}/documents/{document_id}/retry-verification"
        )

        # Assert
        assert response.status_code == 400
        assert response.json()["errorCode"] == "NO_ISSUER_TO_RETRY"

    async def test_the_officer_can_mark_a_land_document_verified_by_hand(self, client):
        # Arrange
        thread_id = await open_thread(client, MISMATCH_APPLICATION_ID)
        await attach(client, thread_id, "land_conversion_certificate.pdf")
        with no_department_reachable():
            frames = await analyze(client, thread_id)
        check_id = issuer_check(settled_document(frames))["checkId"]

        # Act
        response = await client.post(
            f"/api/threads/{thread_id}/checks/{check_id}/resolve",
            data=json.dumps({"action": "manual"}),
            content_type="application/json",
        )

        # Assert
        assert response.status_code == 200
        resolved = response.json()["check"]
        assert resolved["manual"] is True
        assert resolved["status"] == "info"

    async def test_a_land_document_sits_beside_a_pan_that_does_call_a_department(
        self, client
    ):
        # Arrange — one document asks ITD, the other has no department to ask; both
        # seeded on BN/2026/0377
        thread_id = await open_thread(client, MISMATCH_APPLICATION_ID)
        await attach(client, thread_id, "pan_card.pdf")
        await attach(client, thread_id, "encumbrance_certificate.pdf")

        # Act
        with itd_answering(valid_pan):
            frames = await analyze(client, thread_id)

        # Assert
        settled = [
            document for document in read_documents(frames) if document["stage"] == "done"
        ]
        by_type = {document["documentTypeId"]: document for document in settled}
        assert set(by_type) == {"pan", "ec"}
        assert issuer_check(by_type["pan"])["issuerCall"]["issuerServiceId"] == "itd_pan"
        assert issuer_check(by_type["ec"])["issuerCall"] is None
        check_ids = [
            check["checkId"] for document in settled for check in document["checks"]
        ]
        assert len(check_ids) == len(set(check_ids))
        assert read_summary(frames)["documentCount"] == 2
