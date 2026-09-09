"""The Aadhaar story end to end over HTTP.

The department's own wire format is pinned in the adapter tests, and the mocked
UIDAI service in its own view test. Here the department's transport is controlled
directly, because a Django test serves no socket for the backend's outbound call —
which is exactly why `verify:live` exists to drive the real hop.
"""
import json
from contextlib import contextmanager
from typing import Any, Dict, List
from unittest.mock import patch

import httpx
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import AsyncClient

CLEAN_APPLICATION_ID = "BN/2026/0421"
SECOND_APPLICATION_ID = "BN/2026/0398"
AADHAAR_FILENAME = "aadhaar_front.jpg"
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


def checks_by_id(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {check["checkId"]: check for check in document["checks"]}


def issuer_check(document: Dict[str, Any]) -> Dict[str, Any]:
    return next(check for check in document["checks"] if check["group"] == "external")


@contextmanager
def uidai_answering(handler):
    """Substitutes the department's transport, leaving the adapter itself real."""
    from document_verification.adapters.uidai_service_adapter import (
        UidaiServiceAdapter,
    )

    # The registry captures its builder functions at import, so the dict entry is
    # the seam rather than the module attribute.
    with patch.dict(
        UIDAI_BUILDERS,
        {
            "uidai": lambda: UidaiServiceAdapter(
                transport=httpx.MockTransport(handler)
            )
        },
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


class TestAadhaarAnalyze:
    async def test_an_aadhaar_is_identified_read_checked_and_confirmed_by_uidai(
        self, client
    ):
        # Arrange
        thread_id = await open_thread(client, SECOND_APPLICATION_ID)
        await attach(client, thread_id, "aadhaar.pdf")

        # Act
        with uidai_answering(confirming_uidai()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        assert settled["documentTypeId"] == "aadhaar"
        assert settled["implemented"] is True
        assert settled["stage"] == "done"
        assert {value["key"] for value in settled["fieldValues"]} == {
            "name",
            "dob",
            "gender",
            "aadhaarNo",
            "address",
        }
        assert issuer_check(settled)["status"] == "pass"
        assert issuer_check(settled)["issuerCall"]["issuerServiceId"] == "uidai"
        assert settled["status"] == "verified"

    async def test_the_four_steps_are_reported_for_an_aadhaar_as_for_a_pan(
        self, client
    ):
        # Arrange
        thread_id = await open_thread(client, SECOND_APPLICATION_ID)
        await attach(client, thread_id, "aadhaar.pdf")

        # Act
        with uidai_answering(confirming_uidai()):
            frames = await analyze(client, thread_id)

        # Assert
        steps = [
            frame["payload"]["step"]
            for frame in frames
            if frame["type"] == "step" and frame["payload"]["state"] == "done"
        ]
        assert steps == ["identify", "extract", "checks", "verify"]

    async def test_the_seeded_moved_applicant_gets_an_advisory_address_warning(
        self, client
    ):
        # Arrange — the card still carries the holder's previous address
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, AADHAAR_FILENAME)

        # Act
        with uidai_answering(confirming_uidai()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        address_check = checks[f"{document_id}:address"]
        assert address_check["status"] == "warn"
        assert "advisory" in address_check["detail"]
        assert checks[f"{document_id}:name"]["status"] == "pass"
        assert checks[f"{document_id}:dob"]["status"] == "pass"
        assert checks[f"{document_id}:gender"]["status"] == "pass"
        assert checks[f"{document_id}:aadhaar"]["status"] == "pass"
        assert checks[f"{document_id}:aadhaar-format"]["status"] == "pass"
        assert settled["status"] == "attention"

    async def test_the_aadhaar_number_is_masked_everywhere_the_officer_reads_it(
        self, client
    ):
        # Arrange — the sidebar already redacts it; a check detail and a disclosed
        # payload are copied into the permanent file, so they have to agree
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, AADHAAR_FILENAME)

        # Act
        with uidai_answering(confirming_uidai()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        aadhaar_check = checks_by_id(settled)[f"{settled['documentId']}:aadhaar"]
        disclosed = issuer_check(settled)["issuerCall"]["requestPayload"]
        assert "XXXX XXXX 4821" in aadhaar_check["detail"]
        assert "731655204821" not in aadhaar_check["detail"]
        assert disclosed["aadhaarNo"] == "XXXX XXXX 4821"
        assert "731655204821" not in json.dumps(disclosed)

    async def test_a_disagreeing_demographic_warns_rather_than_claiming_confirmation(
        self, client
    ):
        # Arrange — UIDAI holds the number but does not agree on the name
        thread_id = await open_thread(client, SECOND_APPLICATION_ID)
        await attach(client, thread_id, "aadhaar.pdf")

        # Act
        with uidai_answering(confirming_uidai(matched=("dob", "gender"))):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        issuer = issuer_check(settled)
        assert issuer["status"] == "warn"
        assert "does not agree on the name" in issuer["detail"]
        assert "Aadhaar" in issuer["detail"]
        assert settled["status"] == "attention"

    async def test_the_structure_the_aadhaar_template_expects_is_reported(self, client):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, AADHAAR_FILENAME)

        # Act
        with uidai_answering(confirming_uidai()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        assert settled["structureFindings"] == {
            "photo": True,
            "qr": True,
            "emblem": True,
        }
        structure_checks = [
            check for check in settled["checks"] if check["group"] == "structure"
        ]
        assert len(structure_checks) == 3
        assert {check["status"] for check in structure_checks} == {"pass"}

    async def test_a_uidai_timeout_reports_unavailable_and_offers_a_retry(self, client):
        # Arrange — AC7 for a second department
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, AADHAAR_FILENAME)

        # Act
        with uidai_answering(timing_out_uidai()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        issuer = issuer_check(settled)
        assert issuer["status"] == "unavailable"
        assert "No response after" in issuer["detail"]
        assert settled["status"] == "unavailable"

    async def test_an_aadhaar_and_a_pan_on_one_thread_keep_their_own_checks(
        self, client
    ):
        # Arrange — the two identifier checks must not collide on a shared key
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, AADHAAR_FILENAME)
        await attach(client, thread_id, "pan_card.pdf")

        # Act
        with uidai_answering(confirming_uidai()):
            frames = await analyze(client, thread_id)

        # Assert
        documents = {
            document["documentId"]: document for document in read_documents(frames)
        }
        settled = [
            document for document in documents.values() if document["stage"] == "done"
        ]
        assert len(settled) == 2
        assert {document["documentTypeId"] for document in settled} == {
            "aadhaar",
            "pan",
        }
        check_ids = [
            check["checkId"] for document in settled for check in document["checks"]
        ]
        assert len(check_ids) == len(set(check_ids))
        assert f"{settled[0]['documentId']}:aadhaar-format" in check_ids or (
            f"{settled[1]['documentId']}:aadhaar-format" in check_ids
        )
