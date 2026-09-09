"""The Irrigation NOC story end to end over HTTP.

The first clearance letter this build reads, and the first document type whose
issuing department publishes no verification interface. There is nothing to patch a
transport onto here: the point of most of these tests is that no department is called
at all, and that the officer is told so rather than left to notice a missing check.
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
MISMATCH_APPLICATION_ID = "BN/2026/0377"
NOC_FILENAME = "irrigation_noc.pdf"
SEEDED_NOC_NUMBER = "IRR/NOC/2026/0093"
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


def read_steps(frames: List[Dict[str, Any]]) -> List[str]:
    return [
        f"{frame['payload']['step']} {frame['payload']['state']}"
        for frame in frames
        if frame["type"] == "step"
    ]


@contextmanager
def no_department_reachable():
    """Every issuer adapter removed, so any outbound call would fail loudly.

    A NOC needs none. Wrapping the run in this makes the absence of a call an
    assertion rather than an assumption.
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
    return httpx.Response(
        200,
        json={
            "pan": "DQRPK4831L",
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


async def run_noc(client: AsyncClient, application_id: str) -> List[Dict[str, Any]]:
    thread_id = await open_thread(client, application_id)
    await attach(client, thread_id, NOC_FILENAME)
    with no_department_reachable():
        return await analyze(client, thread_id)


class TestIrrigationNocAnalyze:
    async def test_a_noc_is_identified_read_and_checked(self, client):
        # Arrange & Act
        frames = await run_noc(client, MISMATCH_APPLICATION_ID)

        # Assert
        settled = settled_document(frames)
        assert settled["documentTypeId"] == "irrigation_noc"
        assert settled["documentTypeLabel"] == "Irrigation NOC"
        assert settled["implemented"] is True
        assert settled["stage"] == "done"
        assert settled["pageCount"] == 2
        assert {value["key"] for value in settled["fieldValues"]} == {
            "nocNo",
            "issuedBy",
            "issueDate",
            "validUpto",
            "applicant",
            "surveyNo",
            "bufferCondition",
        }

    async def test_the_four_steps_are_reported_as_for_a_pan(self, client):
        # Arrange & Act — a type with no department still reports asking one, because
        # the step ran and reached a verdict; what it found is the check's business
        frames = await run_noc(client, MISMATCH_APPLICATION_ID)

        # Assert
        assert read_steps(frames) == [
            "identify running",
            "identify done",
            "extract running",
            "extract done",
            "checks running",
            "checks done",
            "verify running",
            "verify done",
        ]

    async def test_the_applicant_and_survey_number_are_compared_with_the_application(
        self, client
    ):
        # Arrange & Act
        frames = await run_noc(client, MISMATCH_APPLICATION_ID)

        # Assert
        settled = settled_document(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        assert checks[f"{document_id}:name"]["status"] == "pass"
        assert checks[f"{document_id}:name"]["fieldKey"] == "applicant"
        assert checks[f"{document_id}:survey"]["status"] == "pass"
        assert checks[f"{document_id}:survey"]["fieldKey"] == "surveyNo"

    async def test_a_noc_running_to_2028_reports_valid(self, client):
        # Arrange & Act
        frames = await run_noc(client, MISMATCH_APPLICATION_ID)

        # Assert
        settled = settled_document(frames)
        validity = checks_by_id(settled)[f"{settled['documentId']}:validity"]
        assert validity["status"] == "pass"
        assert validity["title"] == "Valid"
        assert validity["detail"] == "Valid until 09-04-2028."
        assert validity["fieldKey"] == "validUpto"

    async def test_a_noc_that_ran_out_before_today_fails(self, client):
        # Arrange & Act — the seeded lapse: this one ran to May 2026
        frames = await run_noc(client, CLEAN_APPLICATION_ID)

        # Assert
        settled = settled_document(frames)
        validity = checks_by_id(settled)[f"{settled['documentId']}:validity"]
        assert validity["status"] == "fail"
        assert validity["title"] == "Document has expired"
        assert validity["detail"] == "Expired on 21-05-2026."
        assert settled["status"] == "failed"

    async def test_the_lapse_does_not_drag_the_agreeing_fields_with_it(self, client):
        # Arrange & Act
        frames = await run_noc(client, CLEAN_APPLICATION_ID)

        # Assert
        settled = settled_document(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        assert checks[f"{document_id}:name"]["status"] == "pass"
        assert checks[f"{document_id}:survey"]["status"] == "pass"

    async def test_the_noc_number_and_the_buffer_condition_produce_no_checks(
        self, client
    ):
        # Arrange & Act — nothing on the application form to compare either against,
        # and a NOC number has no published structure to validate
        frames = await run_noc(client, MISMATCH_APPLICATION_ID)

        # Assert
        settled = settled_document(frames)
        read_values = {value["key"]: value["value"] for value in settled["fieldValues"]}
        assert read_values["nocNo"] == SEEDED_NOC_NUMBER
        assert read_values["bufferCondition"].startswith("Site lies outside the FTL")
        assert not [
            check
            for check in settled["checks"]
            if check["fieldKey"] in {"nocNo", "issuedBy", "issueDate", "bufferCondition"}
        ]

    async def test_the_two_structural_elements_a_noc_carries_are_reported(self, client):
        # Arrange & Act
        frames = await run_noc(client, MISMATCH_APPLICATION_ID)

        # Assert
        settled = settled_document(frames)
        assert settled["structureFindings"] == {"seal": True, "signature": True}
        structure_checks = [
            check for check in settled["checks"] if check["group"] == "structure"
        ]
        assert len(structure_checks) == 2

    async def test_verification_reports_that_there_is_no_department_to_ask(self, client):
        # Arrange & Act
        frames = await run_noc(client, MISMATCH_APPLICATION_ID)

        # Assert — an external check is still recorded, so the officer sees that the
        # question was reached and answered, not skipped
        settled = settled_document(frames)
        issuer = issuer_check(settled)
        assert issuer["checkId"] == f"{settled['documentId']}:issuer"
        assert issuer["status"] == "info"
        assert issuer["title"] == "No department interface for this Irrigation NOC"
        assert "verify it against the original" in issuer["detail"].lower()
        assert issuer["issuerCall"] is None

    async def test_the_absent_department_does_not_by_itself_hold_the_thread_open(
        self, client
    ):
        # Arrange & Act — nothing an officer can chase, so it is not an open item
        frames = await run_noc(client, MISMATCH_APPLICATION_ID)

        # Assert
        settled = settled_document(frames)
        assert settled["status"] == "verified"
        summary = read_summary(frames)
        assert summary["threadStatus"] == "clear"
        assert summary["openItems"] == []

    async def test_the_officer_can_mark_it_verified_by_hand(self, client):
        # Arrange
        thread_id = await open_thread(client, MISMATCH_APPLICATION_ID)
        await attach(client, thread_id, NOC_FILENAME)
        with no_department_reachable():
            frames = await analyze(client, thread_id)
        settled = settled_document(frames)
        check_id = issuer_check(settled)["checkId"]

        # Act
        response = await client.post(
            f"/api/threads/{thread_id}/checks/{check_id}/resolve",
            data=json.dumps({"action": "manual"}),
            content_type="application/json",
        )

        # Assert — the officer's disposition is recorded beside the verdict, which
        # keeps its own wording
        assert response.status_code == 200
        resolved = response.json()["check"]
        assert resolved["manual"] is True
        assert resolved["status"] == "info"
        assert resolved["title"] == "No department interface for this Irrigation NOC"

    async def test_asking_the_department_again_is_refused(self, client):
        # Arrange
        thread_id = await open_thread(client, MISMATCH_APPLICATION_ID)
        await attach(client, thread_id, NOC_FILENAME)
        with no_department_reachable():
            frames = await analyze(client, thread_id)
        document_id = settled_document(frames)["documentId"]

        # Act
        response = await client.post(
            f"/api/threads/{thread_id}/documents/{document_id}/retry-verification"
        )

        # Assert — there was no call to repeat
        assert response.status_code == 400
        assert response.json()["errorCode"] == "NO_ISSUER_TO_RETRY"

    async def test_correcting_the_survey_number_leaves_the_absent_department_alone(
        self, client
    ):
        # Arrange — an officer's edit cannot conjure a department interface
        thread_id = await open_thread(client, MISMATCH_APPLICATION_ID)
        await attach(client, thread_id, NOC_FILENAME)
        with no_department_reachable():
            frames = await analyze(client, thread_id)
        settled = settled_document(frames)
        document_id = settled["documentId"]

        # Act
        response = await client.patch(
            f"/api/threads/{thread_id}/documents/{document_id}/fields/surveyNo",
            data=json.dumps({"value": "77/3"}),
            content_type="application/json",
        )

        # Assert
        assert response.status_code == 200
        change = response.json()
        rechecked = {check["checkId"]: check for check in change["document"]["checks"]}
        assert rechecked[f"{document_id}:survey"]["status"] == "fail"
        assert rechecked[f"{document_id}:issuer"]["status"] == "info"
        assert rechecked[f"{document_id}:issuer"]["issuerCall"] is None

    async def test_a_noc_sits_alongside_a_pan_on_one_thread(self, client):
        # Arrange — one document asks a department, the other has none to ask
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, "pan_card.pdf")
        await attach(client, thread_id, NOC_FILENAME)

        # Act
        with itd_answering(valid_pan):
            frames = await analyze(client, thread_id)

        # Assert
        settled = [
            document for document in read_documents(frames) if document["stage"] == "done"
        ]
        by_type = {document["documentTypeId"]: document for document in settled}
        assert set(by_type) == {"pan", "irrigation_noc"}
        assert issuer_check(by_type["pan"])["issuerCall"]["issuerServiceId"] == "itd_pan"
        assert issuer_check(by_type["irrigation_noc"])["issuerCall"] is None
        check_ids = [
            check["checkId"] for document in settled for check in document["checks"]
        ]
        assert len(check_ids) == len(set(check_ids))
        assert read_summary(frames)["documentCount"] == 2
