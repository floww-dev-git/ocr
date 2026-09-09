import json
from unittest.mock import patch

import pytest
from django.test import AsyncClient
from django.urls import reverse

from document_scrutiny.constants.analysis_constants import AnalysisEventType
from document_scrutiny.exceptions.scrutiny_exceptions import ScrutinyThreadNotFound

BUILD_INTERACTOR = "api.views.analyze_views.build_analyze_thread_interactor"
THREAD_ID = "thread_1"


def analyze_url(thread_id: str = THREAD_ID) -> str:
    return reverse("stream_thread_analysis", kwargs={"thread_id": thread_id})


def parse_frames(body: bytes):
    frames = []
    for block in body.decode().split("\n\n"):
        if not block.strip():
            continue
        lines = block.split("\n")
        event_type = lines[0].removeprefix("event: ")
        payload = json.loads(lines[1].removeprefix("data: "))
        frames.append((event_type, payload))
    return frames


async def read_body(response) -> bytes:
    chunks = []
    async for chunk in response:
        chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode())
    return b"".join(chunks)


@pytest.fixture
def async_client():
    return AsyncClient()


class TestStreamThreadAnalysis:
    async def test_the_stream_announces_itself_as_an_event_stream(self, async_client):
        # Arrange
        with patch(BUILD_INTERACTOR) as build:
            build.return_value.analyze_thread.return_value = iter(())

            # Act
            response = await async_client.get(analyze_url())
            await read_body(response)

        # Assert
        assert response.status_code == 200
        assert response["Content-Type"] == "text/event-stream"
        assert response["Cache-Control"] == "no-cache"
        assert response["X-Accel-Buffering"] == "no"

    async def test_a_thread_nobody_opened_ends_the_stream_rather_than_hanging(
        self, async_client
    ):
        # Arrange
        def raise_missing(request):
            raise ScrutinyThreadNotFound(thread_id=THREAD_ID)
            yield

        with patch(BUILD_INTERACTOR) as build:
            build.return_value.analyze_thread.side_effect = raise_missing

            # Act
            response = await async_client.get(analyze_url())
            frames = parse_frames(await read_body(response))

        # Assert
        assert [event_type for event_type, _ in frames] == [
            AnalysisEventType.ERROR.value,
            AnalysisEventType.DONE.value,
        ]
        assert "no longer exists" in frames[0][1]["message"]

    async def test_an_unexpected_failure_ends_the_stream_without_leaking_its_text(
        self, async_client
    ):
        # Arrange
        def explode(request):
            raise RuntimeError("psycopg2.OperationalError: secret host down")
            yield

        with patch(BUILD_INTERACTOR) as build:
            build.return_value.analyze_thread.side_effect = explode

            # Act
            response = await async_client.get(analyze_url())
            frames = parse_frames(await read_body(response))

        # Assert
        assert [event_type for event_type, _ in frames] == [
            AnalysisEventType.ERROR.value,
            AnalysisEventType.DONE.value,
        ]
        assert "psycopg2" not in frames[0][1]["message"]
        assert "secret host" not in frames[0][1]["message"]

    async def test_a_failure_part_way_through_keeps_the_frames_already_sent(
        self, async_client
    ):
        # Arrange
        from document_scrutiny.domain.analysis_events import AnalysisEvents
        from document_scrutiny.constants.analysis_constants import AnalysisStep

        def fail_after_first_step(request):
            yield AnalysisEvents.step_running(AnalysisStep.IDENTIFY)
            raise RuntimeError("boom")

        with patch(BUILD_INTERACTOR) as build:
            build.return_value.analyze_thread.side_effect = fail_after_first_step

            # Act
            response = await async_client.get(analyze_url())
            frames = parse_frames(await read_body(response))

        # Assert
        assert [event_type for event_type, _ in frames] == [
            AnalysisEventType.STEP.value,
            AnalysisEventType.ERROR.value,
            AnalysisEventType.DONE.value,
        ]

    async def test_posting_to_the_stream_is_rejected(self, async_client):
        # Arrange
        # Act
        response = await async_client.post(analyze_url())

        # Assert
        assert response.status_code == 405
