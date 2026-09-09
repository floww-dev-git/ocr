import logging
from typing import AsyncIterator, Iterator

from asgiref.sync import sync_to_async
from django.http import HttpRequest, StreamingHttpResponse
from django.views.decorators.http import require_GET

from api.interactor_factory import build_analyze_thread_interactor
from document_scrutiny.domain.analysis_events import AnalysisEvents
from document_scrutiny.dtos.analysis_dtos import AnalysisEventDTO, AnalyzeThreadRequestDTO
from document_scrutiny.exceptions.scrutiny_exceptions import ScrutinyThreadNotFound
from document_scrutiny.presenters.scrutiny_stream_presenter import (
    ScrutinyStreamPresenter,
)

logger = logging.getLogger(__name__)

EVENT_STREAM_CONTENT_TYPE = "text/event-stream"
THREAD_MISSING_MESSAGE = "That scrutiny thread no longer exists. Start a new one."
UNEXPECTED_STREAM_MESSAGE = (
    "Something went wrong while reading these documents. Nothing further was recorded."
)

_STREAM_END = object()


@require_GET
async def stream_thread_analysis(
    request: HttpRequest, thread_id: str
) -> StreamingHttpResponse:
    response = StreamingHttpResponse(
        _analysis_frames(thread_id=thread_id),
        content_type=EVENT_STREAM_CONTENT_TYPE,
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


async def _analysis_frames(thread_id: str) -> AsyncIterator[str]:
    read_next = sync_to_async(_read_next_event, thread_sensitive=False)
    close = sync_to_async(_close_events, thread_sensitive=False)
    events = None
    try:
        events = _build_event_iterator(thread_id=thread_id)
        while True:
            try:
                event = await read_next(events)
            except ScrutinyThreadNotFound:
                yield _frame(AnalysisEvents.error(THREAD_MISSING_MESSAGE))
                yield _frame(AnalysisEvents.done())
                return
            except Exception:
                logger.exception("Analysis stream failed for thread %s", thread_id)
                yield _frame(AnalysisEvents.error(UNEXPECTED_STREAM_MESSAGE))
                yield _frame(AnalysisEvents.done())
                return
            if event is _STREAM_END:
                return
            yield _frame(event)
    finally:
        # Closing the sync generator is what lets it run its own cleanup and
        # settle a half-read document, rather than waiting on garbage collection
        # after the officer has already navigated away.
        if events is not None:
            await close(events)


def _build_event_iterator(thread_id: str) -> Iterator[AnalysisEventDTO]:
    interactor = build_analyze_thread_interactor()
    return iter(
        interactor.analyze_thread(request=AnalyzeThreadRequestDTO(thread_id=thread_id))
    )


def _read_next_event(events: Iterator[AnalysisEventDTO]):
    try:
        return next(events)
    except StopIteration:
        return _STREAM_END


def _close_events(events: Iterator[AnalysisEventDTO]) -> None:
    closer = getattr(events, "close", None)
    if closer is None:
        return
    try:
        closer()
    except Exception:
        logger.exception("Closing the analysis stream failed")


def _frame(event: AnalysisEventDTO) -> str:
    return ScrutinyStreamPresenter.format_frame(event=event)
