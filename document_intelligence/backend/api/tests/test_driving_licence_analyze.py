"""The driving licence story end to end over HTTP.

The department's transport is controlled directly, as in the Aadhaar tests: a Django
test serves no socket for the backend's outbound call. Sarathi's own wire format is
pinned in its adapter tests and its mocked service in its own view test.
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
LICENCE_FILENAME = "driving_licence.pdf"
SEEDED_LICENCE = "TS0920150012345"
ADAPTER_BUILDERS = (
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


def read_summary(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
    return next(frame["payload"] for frame in frames if frame["type"] == "summary")


@contextmanager
def sarathi_answering(handler):
    from document_verification.adapters.sarathi_service_adapter import (
        SarathiServiceAdapter,
    )

    with patch.dict(
        ADAPTER_BUILDERS,
        {
            "sarathi": lambda: SarathiServiceAdapter(
                transport=httpx.MockTransport(handler)
            )
        },
    ):
        yield


def active_licence(name_match: bool = True, date_of_birth_match: bool = True):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "dlNo": SEEDED_LICENCE,
                "status": "ACTIVE",
                "holder": "SRINIVAS RAO KANDULA",
                "dob": "1978-08-14",
                "validUpto": "2035-06-30",
                "cov": ["LMV", "MCWG"],
                "nameMatch": name_match,
                "dobMatch": date_of_birth_match,
            },
        )

    return handler


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


class TestDrivingLicenceAnalyze:
    async def test_a_licence_is_identified_read_and_checked(self, client):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LICENCE_FILENAME)

        # Act
        with sarathi_answering(active_licence()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        assert settled["documentTypeId"] == "dl"
        assert settled["implemented"] is True
        assert settled["stage"] == "done"
        assert settled["pageCount"] == 2
        assert {value["key"] for value in settled["fieldValues"]} == {
            "name",
            "dob",
            "dlNo",
            "validUpto",
            "address",
            "bloodGroup",
        }

    async def test_the_seeded_year_of_birth_discrepancy_fails(self, client):
        # Arrange — the licence reads 1978, the application form says 1979
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LICENCE_FILENAME)

        # Act
        with sarathi_answering(active_licence(date_of_birth_match=False)):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        date_check = checks[f"{document_id}:dob"]
        assert date_check["status"] == "fail"
        assert "14-08-1978" in date_check["detail"]
        assert "14-08-1979" in date_check["detail"]
        assert settled["status"] == "failed"

    async def test_the_name_and_address_still_agree_alongside_the_failure(self, client):
        # Arrange — one failing field must not drag the others with it
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LICENCE_FILENAME)

        # Act
        with sarathi_answering(active_licence()):
            frames = await analyze(client, thread_id)

        # Assert
        checks = checks_by_id(settled_document(frames))
        document_id = settled_document(frames)["documentId"]
        assert checks[f"{document_id}:name"]["status"] == "pass"
        assert checks[f"{document_id}:address"]["status"] == "pass"

    async def test_a_licence_running_to_2035_reports_valid(self, client):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LICENCE_FILENAME)

        # Act
        with sarathi_answering(active_licence()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        validity_check = checks_by_id(settled)[f"{settled['documentId']}:validity"]
        assert validity_check["status"] == "pass"
        assert validity_check["title"] == "Valid"
        assert validity_check["detail"] == "Valid until 30-06-2035."
        assert validity_check["fieldKey"] == "validUpto"

    async def test_the_licence_number_gets_a_format_check_but_no_application_check(
        self, client
    ):
        # Arrange — there is no licence number on the application form to compare to
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LICENCE_FILENAME)

        # Act
        with sarathi_answering(active_licence()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        assert checks[f"{document_id}:licence-format"]["status"] == "pass"
        assert f"{document_id}:dlNo" not in checks

    async def test_the_blood_group_is_read_but_produces_no_check(self, client):
        # Arrange — nothing to compare it against and no published structure
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LICENCE_FILENAME)

        # Act
        with sarathi_answering(active_licence()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        read_values = {value["key"]: value["value"] for value in settled["fieldValues"]}
        assert read_values["bloodGroup"] == "B+"
        assert not [
            check
            for check in settled["checks"]
            if check["fieldKey"] == "bloodGroup"
        ]

    async def test_sarathi_confirms_the_licence_and_discloses_what_it_holds(
        self, client
    ):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LICENCE_FILENAME)

        # Act
        with sarathi_answering(active_licence()):
            frames = await analyze(client, thread_id)

        # Assert
        issuer = issuer_check(settled_document(frames))
        assert issuer["status"] == "pass"
        assert issuer["issuerCall"]["issuerServiceId"] == "sarathi"
        assert issuer["issuerCall"]["requestPayload"]["dlNo"] == SEEDED_LICENCE
        assert issuer["issuerCall"]["responsePayload"]["validUpto"] == "2035-06-30"
        assert issuer["issuerCall"]["responsePayload"]["cov"] == ["LMV", "MCWG"]

    async def test_the_two_structural_elements_a_licence_carries_are_reported(
        self, client
    ):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LICENCE_FILENAME)

        # Act
        with sarathi_answering(active_licence()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = settled_document(frames)
        assert settled["structureFindings"] == {"photo": True, "hologram": True}
        structure_checks = [
            check for check in settled["checks"] if check["group"] == "structure"
        ]
        assert len(structure_checks) == 2

    async def test_correcting_the_year_of_birth_settles_the_check(self, client):
        # Arrange — AC8 over a third document type
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LICENCE_FILENAME)
        with sarathi_answering(active_licence(date_of_birth_match=False)):
            frames = await analyze(client, thread_id)
        settled = settled_document(frames)
        document_id = settled["documentId"]

        # Act
        response = await client.patch(
            f"/api/threads/{thread_id}/documents/{document_id}/fields/dob",
            data=json.dumps({"value": "1979-08-14"}),
            content_type="application/json",
        )

        # Assert
        assert response.status_code == 200
        change = response.json()
        assert change["changedCheckIds"] == [f"{document_id}:dob"]
        corrected = {
            check["checkId"]: check for check in change["document"]["checks"]
        }
        assert corrected[f"{document_id}:dob"]["status"] == "pass"
        assert corrected[f"{document_id}:validity"]["status"] == "pass"

    async def test_all_three_identity_documents_can_sit_on_one_thread(self, client):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, "aadhaar_front.jpg")
        await attach(client, thread_id, "pan_card.pdf")
        await attach(client, thread_id, LICENCE_FILENAME)

        # Act
        with sarathi_answering(active_licence()):
            frames = await analyze(client, thread_id)

        # Assert
        documents = {
            document["documentId"]: document for document in read_documents(frames)
        }
        settled = [
            document for document in documents.values() if document["stage"] == "done"
        ]
        assert {document["documentTypeId"] for document in settled} == {
            "aadhaar",
            "pan",
            "dl",
        }
        check_ids = [
            check["checkId"] for document in settled for check in document["checks"]
        ]
        assert len(check_ids) == len(set(check_ids))
        assert read_summary(frames)["documentCount"] == 3
