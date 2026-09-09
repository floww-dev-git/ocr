"""A bundled deed file, end to end over HTTP.

One upload becomes four rows: the file itself, closed off with a note of what was
found in it, and the three registered deeds inside it, each read and checked in its
own right. The registrar's transport is controlled directly, as in the other issuer
tests: a Django test serves no socket for the backend's outbound call.
"""
import json
from contextlib import contextmanager
from typing import Any, Dict, List
from unittest.mock import patch

import httpx
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import AsyncClient

BUNDLE_APPLICATION_ID = "BN/2026/0455"
CLEAN_CHAIN = "01_clean_chain.pdf"
GAP_BUNDLE = "03_gap_extent_overflow.pdf"
EXPECTED_DEED_COUNT = 3
EXPECTED_ROW_COUNT = 4

ADAPTER_BUILDERS = (
    "document_verification.adapters.issuer_adapter_registry"
    "._ADAPTER_BUILDERS_BY_ISSUER_SERVICE"
)

# What the register holds for the parcel the bundles are written over.
IGRS_RECORDS = {
    "1188/2003": ("GOVIND RAO", "RAMESH KUMAR"),
    "2451/2011": ("RAMESH KUMAR", "SUNITA SHARMA"),
    "5820/2019": ("SUNITA SHARMA", "PRAKASH IYER"),
}


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


def settled_documents(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest = {
        frame["payload"]["documentId"]: frame["payload"]
        for frame in frames
        if frame["type"] == "doc"
    }
    return list(latest.values())


def the_bundle(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
    return next(
        document
        for document in settled_documents(frames)
        if document["parentDocumentId"] is None
    )


def the_deeds_inside(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        (
            document
            for document in settled_documents(frames)
            if document["parentDocumentId"] is not None
        ),
        key=lambda document: document["pageStart"],
    )


def the_summary(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
    return next(frame["payload"] for frame in frames if frame["type"] == "summary")


def registering_igrs():
    def handler(request: httpx.Request) -> httpx.Response:
        doc_no = str(request.url.path).split("/mock/igrs/deeds/", 1)[-1]
        executant, claimant = IGRS_RECORDS.get(doc_no, ("", ""))
        if not claimant:
            return httpx.Response(
                200, json={"docNo": doc_no, "status": "NOT_FOUND", "nameMatch": None}
            )
        submitted_name = request.url.params.get("name", "")
        return httpx.Response(
            200,
            json={
                "docNo": doc_no,
                "status": "REGISTERED",
                "sro": "Serilingampally",
                "executant": executant,
                "claimant": claimant,
                "extent": "400 SQ.YDS",
                "nameMatch": submitted_name.upper() == claimant,
            },
        )

    return handler


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


async def run_bundle(client: AsyncClient, filename: str) -> List[Dict[str, Any]]:
    thread_id = await open_thread(client, BUNDLE_APPLICATION_ID)
    await attach(client, thread_id, filename)
    with igrs_answering(registering_igrs()):
        return await analyze(client, thread_id)


class TestAnalyzingABundledDeedFile:
    async def test_one_upload_becomes_the_file_plus_every_deed_inside_it(self, client):
        # Act
        frames = await run_bundle(client, CLEAN_CHAIN)

        # Assert
        assert len(settled_documents(frames)) == EXPECTED_ROW_COUNT
        assert len(the_deeds_inside(frames)) == EXPECTED_DEED_COUNT

    async def test_the_file_itself_reports_what_was_found_in_it(self, client):
        # Act
        frames = await run_bundle(client, CLEAN_CHAIN)
        bundle = the_bundle(frames)

        # Assert
        assert [check["status"] for check in bundle["checks"]] == ["info"]
        assert bundle["checks"][0]["title"] == "3 documents found in this file"
        assert "Pages 1-2: Link document." in bundle["checks"][0]["detail"]
        assert "Pages 5-6: Sale deed." in bundle["checks"][0]["detail"]

    async def test_the_file_itself_is_closed_off_without_being_read(self, client):
        """It has no single vendor, extent or registration number to check, so there
        is nothing on it to compare against the application."""
        # Act
        bundle = the_bundle(await run_bundle(client, CLEAN_CHAIN))

        # Assert
        assert bundle["stage"] == "done"
        assert bundle["status"] == "verified"
        assert bundle["fieldValues"] == []
        assert bundle["deedRecord"] is None

    async def test_each_deed_names_the_pages_it_occupies(self, client):
        # Act
        deeds = the_deeds_inside(await run_bundle(client, CLEAN_CHAIN))

        # Assert
        assert [(deed["pageStart"], deed["pageEnd"]) for deed in deeds] == [
            (0, 1),
            (2, 3),
            (4, 5),
        ]
        assert all(deed["pageCount"] == 2 for deed in deeds)

    async def test_each_deed_keeps_the_name_of_the_file_it_came_out_of(self, client):
        # Act
        deeds = the_deeds_inside(await run_bundle(client, CLEAN_CHAIN))

        # Assert
        assert {deed["filename"] for deed in deeds} == {CLEAN_CHAIN}

    async def test_only_the_deed_being_relied_on_is_read_as_the_sale_deed(self, client):
        """Reading all three as the current deed would ask the officer why a 2003
        vendor is not the applicant."""
        # Act
        deeds = the_deeds_inside(await run_bundle(client, CLEAN_CHAIN))

        # Assert
        assert [deed["documentTypeId"] for deed in deeds] == [
            "link_doc",
            "link_doc",
            "sale_deed",
        ]

    async def test_only_the_current_deed_is_compared_to_the_applicant(self, client):
        """A prior owner is not the applicant, and saying so would be noise."""
        # Act
        deeds = the_deeds_inside(await run_bundle(client, CLEAN_CHAIN))
        name_checks = [
            [check for check in deed["checks"] if check["fieldKey"] == "purchaser"]
            for deed in deeds
        ]

        # Assert
        assert [len(checks) for checks in name_checks] == [0, 0, 1]
        assert name_checks[-1][0]["status"] == "pass"

    async def test_the_chain_hands_over_from_one_deed_to_the_next(self, client):
        # Act
        deeds = the_deeds_inside(await run_bundle(client, CLEAN_CHAIN))
        records = [deed["deedRecord"] for deed in deeds]

        # Assert — every seller is the previous buyer, and cites that deed
        assert [record["docNo"] for record in records] == [
            "1188/2003",
            "2451/2011",
            "5820/2019",
        ]
        assert [record["sellers"][0]["name"] for record in records] == [
            "Govind Rao",
            "Ramesh Kumar",
            "Sunita Sharma",
        ]
        assert [record["buyers"][0]["name"] for record in records] == [
            "Ramesh Kumar",
            "Sunita Sharma",
            "Prakash Iyer",
        ]
        assert [list(record["priorDeedRefs"]) for record in records] == [
            [],
            ["1188/2003"],
            ["2451/2011"],
        ]

    async def test_a_party_is_read_with_enough_detail_to_tell_people_apart(
        self, client
    ):
        # Act
        deeds = the_deeds_inside(await run_bundle(client, CLEAN_CHAIN))
        seller = deeds[0]["deedRecord"]["sellers"][0]

        # Assert
        assert seller["relation"] == "s/o"
        assert seller["relativeName"] == "Narsimha Rao"

    async def test_the_registrar_is_asked_about_every_deed_separately(self, client):
        # Act
        frames = await run_bundle(client, CLEAN_CHAIN)
        issuer_checks = [
            check
            for document in settled_documents(frames)
            for check in document["checks"]
            if check["group"] == "external"
        ]

        # Assert
        assert len(issuer_checks) == EXPECTED_DEED_COUNT
        assert {check["status"] for check in issuer_checks} == {"pass"}
        assert sorted(
            check["issuerCall"]["requestPayload"]["docNo"] for check in issuer_checks
        ) == ["1188/2003", "2451/2011", "5820/2019"]

    async def test_the_bundle_itself_is_never_sent_to_the_registrar(self, client):
        """There is no registration number for a photocopy of four deeds."""
        # Act
        bundle = the_bundle(await run_bundle(client, CLEAN_CHAIN))

        # Assert
        assert [check["group"] for check in bundle["checks"]] == ["rule"]

    async def test_a_clean_bundle_leaves_the_thread_clear(self, client):
        # Act
        summary = the_summary(await run_bundle(client, CLEAN_CHAIN))

        # Assert
        assert summary["threadStatus"] == "clear"
        assert summary["documentCount"] == EXPECTED_ROW_COUNT
        assert summary["openItems"] == []

    async def test_every_deed_finishes_rather_than_sitting_queued_behind_the_bundle(
        self, client
    ):
        """The deeds appear mid-run, so the pass loop has to pick them up."""
        # Act
        frames = await run_bundle(client, CLEAN_CHAIN)

        # Assert
        assert all(
            document["stage"] == "done" for document in settled_documents(frames)
        )

    async def test_the_stream_closes_with_summary_then_chain_then_done(self, client):
        """Title can only be traced once every deed in the run has been read, so the
        chain frame arrives after the summary and before the run closes."""
        # Act
        frames = await run_bundle(client, CLEAN_CHAIN)
        tail = [frame["type"] for frame in frames][-3:]

        # Assert
        assert tail == ["summary", "chain", "done"]

    async def test_the_chain_frame_carries_the_ownership_report(self, client):
        # Act
        frames = await run_bundle(client, CLEAN_CHAIN)
        chain = next(
            frame["payload"] for frame in frames if frame["type"] == "chain"
        )

        # Assert
        assert chain["verdict"]["level"] == "clean"
        assert chain["chain"]["overall"] == "intact"
        assert chain["stats"]["titleDeedCount"] == EXPECTED_DEED_COUNT
        assert [entry["party"]["name"] for entry in chain["journey"] if entry["kind"] == "owner"][0] == "Prakash Iyer"

    async def test_a_broken_bundle_reports_a_broken_chain_in_the_frame(self, client):
        # Act
        frames = await run_bundle(client, "04_broken_stranger_seller.pdf")
        chain = next(
            frame["payload"] for frame in frames if frame["type"] == "chain"
        )

        # Assert
        assert chain["verdict"]["level"] == "broken"
        assert chain["risk"]["level"] == "High"
        assert chain["attention"][0]["verb"] == "RESOLVE"


class TestAThreadWithoutDeeds:
    @pytest.fixture(autouse=True)
    def mock_extraction(self, settings):
        settings.EXTRACTION_MODE = "mock"
        settings.MOCK_ISSUER_LATENCY_SECONDS = 0
        settings.SCRUTINY_TODAY = "2026-09-07"

    @pytest.fixture
    def client(self) -> AsyncClient:
        return AsyncClient()

    async def test_a_pan_only_thread_emits_no_chain_frame(self, client):
        """There is no title to trace, so the officer is told nothing about one."""
        # Arrange
        thread = await client.post(
            "/api/threads",
            data=json.dumps({"applicationId": "BN/2026/0421"}),
            content_type="application/json",
        )
        thread_id = thread.json()["threadId"]
        await client.post(
            f"/api/threads/{thread_id}/documents",
            data={
                "files": SimpleUploadedFile("pan_card.jpg", b"not-a-real-scan")
            },
        )

        # Act
        response = await client.get(f"/api/threads/{thread_id}/analyze")
        body = b"".join(
            [chunk async for chunk in response.streaming_content]
        ).decode()
        frames = read_frames(body)

        # Assert
        assert not any(frame["type"] == "chain" for frame in frames)
        assert [frame["type"] for frame in frames][-2:] == ["summary", "done"]

    async def test_a_bundle_that_conveys_more_land_than_it_holds_needs_attention(
        self, client
    ):
        """The 2019 deed conveys 600 sq.yd against an application for 400."""
        # Act
        frames = await run_bundle(client, GAP_BUNDLE)
        current = the_deeds_inside(frames)[-1]

        # Assert
        assert the_summary(frames)["threadStatus"] == "attention"
        extent = next(
            check for check in current["checks"] if check["fieldKey"] == "extent"
        )
        assert extent["status"] == "warn"
        assert current["deedRecord"]["property"]["extentSqYard"] == 600.0


BUNDLE_VERDICTS = {
    CLEAN_CHAIN: ("intact", ("linked", "linked")),
    "02_weak_transliteration.pdf": ("review", ("linked", "weak")),
    GAP_BUNDLE: ("review", ("linked", "gap")),
    "04_broken_stranger_seller.pdf": ("broken", ("linked", "broken")),
}


async def attach_and_analyze(client: AsyncClient, filename: str) -> str:
    """Runs the real pipeline and hands back the thread it left behind."""
    thread_id = await open_thread(client, BUNDLE_APPLICATION_ID)
    await attach(client, thread_id, filename)
    with igrs_answering(registering_igrs()):
        await analyze(client, thread_id)
    return thread_id


def trace_title(thread_id: str):
    from document_scrutiny.dtos.chain_dtos import ChainOfTitleRequestDTO
    from document_scrutiny.interactors.get_chain_of_title_interactor import (
        GetChainOfTitleInteractor,
    )
    from document_scrutiny.storages.in_memory_scrutiny_thread_storage import (
        InMemoryScrutinyThreadStorage,
    )

    return GetChainOfTitleInteractor(
        thread_storage=InMemoryScrutinyThreadStorage()
    ).get_chain_of_title(request=ChainOfTitleRequestDTO(thread_id=thread_id))


class TestTracingTitleAcrossASegmentedBundle:
    """The chain read off real thread state, after the real reading pipeline.

    The unit tests grade the fixtures. This grades what actually reached storage —
    segmentation, per-slice reads and all — which is the only way to know the two agree.
    """

    @pytest.mark.parametrize(
        "filename", sorted(BUNDLE_VERDICTS), ids=sorted(BUNDLE_VERDICTS)
    )
    async def test_each_bundle_traces_to_the_verdict_it_was_built_to_produce(
        self, client, filename
    ):
        # Arrange
        expected_overall, expected_links = BUNDLE_VERDICTS[filename]
        thread_id = await attach_and_analyze(client, filename)

        # Act
        chain = trace_title(thread_id)

        # Assert
        assert chain.overall == expected_overall
        assert tuple(link.verdict for link in chain.links) == expected_links

    async def test_the_chain_runs_through_the_three_deeds_the_bundle_held(
        self, client
    ):
        # Arrange
        thread_id = await attach_and_analyze(client, CLEAN_CHAIN)

        # Act
        chain = trace_title(thread_id)

        # Assert
        assert [link.from_doc_no for link in chain.links] == ["1188/2003", "2451/2011"]
        assert [link.to_doc_no for link in chain.links] == ["2451/2011", "5820/2019"]

    async def test_the_bundle_row_itself_is_not_a_link_in_the_chain(self, client):
        # Arrange
        thread_id = await attach_and_analyze(client, CLEAN_CHAIN)

        # Act
        chain = trace_title(thread_id)

        # Assert
        assert len(chain.ordered_document_ids) == EXPECTED_DEED_COUNT

    async def test_the_break_a_document_level_check_cannot_see_is_found_here(
        self, client
    ):
        """Every check on the broken bundle's deeds passes on its own; only tracing the
        chain shows that its 2019 vendor was never a buyer in it."""
        # Arrange
        frames = await run_bundle(client, "04_broken_stranger_seller.pdf")
        thread_id = await attach_and_analyze(client, "04_broken_stranger_seller.pdf")

        # Act
        chain = trace_title(thread_id)

        # Assert
        deed_checks = [
            check
            for document in settled_documents(frames)
            for check in document["checks"]
            if check["status"] not in ("pass", "info")
        ]
        assert deed_checks == []
        assert chain.overall == "broken"
        assert "Mohammed Farooq" in chain.findings[0].detail
