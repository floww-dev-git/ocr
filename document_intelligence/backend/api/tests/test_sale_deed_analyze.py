"""The sale deed story end to end over HTTP.

The registrar's transport is controlled directly, as in the other issuer tests: a
Django test serves no socket for the backend's outbound call. IGRS's own wire format
is pinned in its adapter tests and its mocked service in its own view test.
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
SALE_DEED_FILENAME = "sale_deed_2019.pdf"
LINK_DOCUMENT_FILENAME = "link_deed_2009.pdf"
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


def settled_documents(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest = {
        document["documentId"]: document for document in read_documents(frames)
    }
    return [
        document for document in latest.values() if document["stage"] == "done"
    ]


def only_settled(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
    settled = settled_documents(frames)
    assert len(settled) == 1
    return settled[0]


def checks_by_id(document: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {check["checkId"]: check for check in document["checks"]}


def issuer_check(document: Dict[str, Any]) -> Dict[str, Any]:
    return next(check for check in document["checks"] if check["group"] == "external")


@contextmanager
def igrs_answering(handler):
    from document_verification.adapters.igrs_deed_service_adapter import (
        IgrsDeedServiceAdapter,
    )

    with patch.dict(
        ADAPTER_BUILDERS,
        {
            "igrs": lambda: IgrsDeedServiceAdapter(
                transport=httpx.MockTransport(handler)
            )
        },
    ):
        yield


def registering_igrs(name_match: bool = True):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "status": "REGISTERED",
                "sro": "Quthbullapur",
                "executant": "PADMAVATHI RENTALA",
                "claimant": "SRINIVAS RAO KANDULA",
                "extent": "267 SQ.YDS",
                "registrationDate": "2019-03-12",
                "nameMatch": name_match,
            },
        )

    return handler


def unreachable_igrs():
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


class TestSaleDeedAnalyze:
    async def test_a_sale_deed_is_identified_read_and_checked(self, client):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)

        # Act
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = only_settled(frames)
        assert settled["documentTypeId"] == "sale_deed"
        assert settled["implemented"] is True
        assert settled["pageCount"] == 14
        assert {value["key"] for value in settled["fieldValues"]} == {
            "docNo",
            "regDate",
            "sro",
            "vendor",
            "purchaser",
            "surveyNo",
            "plotNo",
            "extent",
            "village",
            "consideration",
            "boundaries",
        }

    async def test_the_deed_is_compared_against_the_application_field_by_field(
        self, client
    ):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)

        # Act
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = only_settled(frames)
        checks = checks_by_id(settled)
        document_id = settled["documentId"]
        assert checks[f"{document_id}:name"]["status"] == "pass"
        assert checks[f"{document_id}:survey"]["status"] == "pass"
        assert checks[f"{document_id}:plot"]["status"] == "pass"
        assert checks[f"{document_id}:extent"]["status"] == "pass"
        assert checks[f"{document_id}:village"]["status"] == "pass"

    async def test_the_four_structural_elements_a_deed_carries_are_reported(
        self, client
    ):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)

        # Act
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = only_settled(frames)
        assert settled["structureFindings"] == {
            "schedule": True,
            "stamp": True,
            "registration": True,
            "witnesses": True,
        }

    async def test_the_registrar_confirms_the_deed_and_discloses_what_it_holds(
        self, client
    ):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)

        # Act
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)

        # Assert
        issuer = issuer_check(only_settled(frames))
        assert issuer["status"] == "pass"
        assert issuer["issuerCall"]["issuerServiceId"] == "igrs"
        assert issuer["issuerCall"]["requestPayload"]["docNo"] == "4821/2019"
        assert issuer["issuerCall"]["responsePayload"]["executant"] == (
            "PADMAVATHI RENTALA"
        )

    async def test_a_deed_registered_to_someone_else_warns(self, client):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)

        # Act
        with igrs_answering(registering_igrs(name_match=False)):
            frames = await analyze(client, thread_id)

        # Assert
        settled = only_settled(frames)
        issuer = issuer_check(settled)
        assert issuer["status"] == "warn"
        assert "Sale deed" in issuer["detail"]
        assert settled["status"] == "attention"

    async def test_an_unreachable_registrar_reports_unavailable(self, client):
        # Arrange — AC7 for a fourth department
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)

        # Act
        with igrs_answering(unreachable_igrs()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = only_settled(frames)
        assert issuer_check(settled)["status"] == "unavailable"
        assert settled["status"] == "unavailable"


class TestSaleDeedCarriesItsStructuredRecord:
    async def test_the_deed_record_rides_alongside_the_flat_values(self, client):
        # Arrange — the chain engine reads this, not the flattened names
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)

        # Act
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)

        # Assert
        deed_record = only_settled(frames)["deedRecord"]
        assert deed_record is not None
        assert deed_record["docNo"] == "4821/2019"
        assert deed_record["deedType"] == "Sale Deed"
        assert deed_record["priorDeedRefs"] == ["2210/2009"]
        assert deed_record["property"]["extentSqYard"] == 267.0
        assert [party["name"] for party in deed_record["sellers"]] == [
            "Padmavathi Rentala"
        ]
        assert [party["name"] for party in deed_record["buyers"]] == [
            "Srinivas Rao Kandula"
        ]

    async def test_an_identity_document_carries_no_deed_record(self, client):
        # Arrange — the field is nullable and stays null for anything that is not a deed
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, "pan_card.pdf")

        # Act
        frames = await analyze(client, thread_id)

        # Assert
        assert only_settled(frames)["deedRecord"] is None

    async def test_a_link_document_is_read_as_the_prior_owners_purchase(self, client):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, LINK_DOCUMENT_FILENAME)

        # Act
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)

        # Assert
        settled = only_settled(frames)
        assert settled["documentTypeId"] == "link_doc"
        read_keys = {value["key"] for value in settled["fieldValues"]}
        assert "consideration" not in read_keys
        assert "boundaries" not in read_keys
        deed_record = settled["deedRecord"]
        assert deed_record["docNo"] == "2210/2009"
        assert [party["name"] for party in deed_record["buyers"]] == [
            "Padmavathi Rentala"
        ]

    async def test_the_deed_and_its_link_document_hand_over_to_each_other(self, client):
        # Arrange — the sale deed's vendor is the link document's purchaser, which is
        # what a chain of title is made of
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)
        await attach(client, thread_id, LINK_DOCUMENT_FILENAME)

        # Act
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)

        # Assert
        by_type = {
            document["documentTypeId"]: document
            for document in settled_documents(frames)
        }
        assert set(by_type) == {"sale_deed", "link_doc"}
        sale_deed = by_type["sale_deed"]["deedRecord"]
        link_document = by_type["link_doc"]["deedRecord"]
        assert sale_deed["sellers"][0]["name"] == link_document["buyers"][0]["name"]
        assert sale_deed["priorDeedRefs"] == [link_document["docNo"]]


class TestSaleDeedDisagreements:
    async def test_a_corrected_survey_number_settles_its_check(self, client):
        # Arrange — AC8 over the deed
        thread_id = await open_thread(client, MISMATCH_APPLICATION_ID)
        await attach(client, thread_id, "sale_deed_2020.pdf")
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)
        settled = only_settled(frames)
        document_id = settled["documentId"]

        # Act — misread it, then put it back
        broken = await client.patch(
            f"/api/threads/{thread_id}/documents/{document_id}/fields/surveyNo",
            data=json.dumps({"value": "77/9"}),
            content_type="application/json",
        )
        fixed = await client.patch(
            f"/api/threads/{thread_id}/documents/{document_id}/fields/surveyNo",
            data=json.dumps({"value": "77/2"}),
            content_type="application/json",
        )

        # Assert
        broken_checks = {
            check["checkId"]: check for check in broken.json()["document"]["checks"]
        }
        fixed_checks = {
            check["checkId"]: check for check in fixed.json()["document"]["checks"]
        }
        assert broken_checks[f"{document_id}:survey"]["status"] == "fail"
        assert fixed_checks[f"{document_id}:survey"]["status"] == "pass"

    async def test_a_survey_number_disagreement_fails_but_a_plot_number_warns(
        self, client
    ):
        # Arrange — the survey number identifies the parcel; a plot number is local
        # convention and gets renumbered
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)
        document_id = only_settled(frames)["documentId"]

        # Act
        survey = await client.patch(
            f"/api/threads/{thread_id}/documents/{document_id}/fields/surveyNo",
            data=json.dumps({"value": "999/9"}),
            content_type="application/json",
        )
        plot = await client.patch(
            f"/api/threads/{thread_id}/documents/{document_id}/fields/plotNo",
            data=json.dumps({"value": "999"}),
            content_type="application/json",
        )

        # Assert
        survey_checks = {
            check["checkId"]: check for check in survey.json()["document"]["checks"]
        }
        plot_checks = {
            check["checkId"]: check for check in plot.json()["document"]["checks"]
        }
        assert survey_checks[f"{document_id}:survey"]["status"] == "fail"
        assert plot_checks[f"{document_id}:plot"]["status"] == "warn"

    async def test_an_extent_written_another_way_still_agrees(self, client):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)
        document_id = only_settled(frames)["documentId"]

        # Act
        response = await client.patch(
            f"/api/threads/{thread_id}/documents/{document_id}/fields/extent",
            data=json.dumps({"value": "267 Sq. Yards (223.25 Sq. Metres)"}),
            content_type="application/json",
        )

        # Assert
        checks = {
            check["checkId"]: check for check in response.json()["document"]["checks"]
        }
        assert checks[f"{document_id}:extent"]["status"] == "pass"

    async def test_an_extent_that_does_not_match_warns_rather_than_failing(
        self, client
    ):
        # Arrange
        thread_id = await open_thread(client, CLEAN_APPLICATION_ID)
        await attach(client, thread_id, SALE_DEED_FILENAME)
        with igrs_answering(registering_igrs()):
            frames = await analyze(client, thread_id)
        document_id = only_settled(frames)["documentId"]

        # Act
        response = await client.patch(
            f"/api/threads/{thread_id}/documents/{document_id}/fields/extent",
            data=json.dumps({"value": "600 sq. yds"}),
            content_type="application/json",
        )

        # Assert
        checks = {
            check["checkId"]: check for check in response.json()["document"]["checks"]
        }
        assert checks[f"{document_id}:extent"]["status"] == "warn"
