from typing import Iterator, List, Set

from document_scrutiny.constants.analysis_constants import (
    MAX_ANALYSIS_PASSES,
    UNEXPECTED_FAILURE_MESSAGE,
    AnalysisEventType,
)
from document_scrutiny.constants.enums import DocumentStage
from document_scrutiny.domain.analysis_events import AnalysisEvents
from document_scrutiny.domain.scrutiny_summary import ScrutinySummary
from document_scrutiny.dtos.analysis_dtos import (
    AnalysisEventDTO,
    AnalyzeDocumentRequestDTO,
    AnalyzeThreadRequestDTO,
)
from document_scrutiny.adapters.failure_reporter_interface import (
    FailureReporterInterface,
)
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.ownership_report_dtos import OwnershipReportRequestDTO
from document_scrutiny.interactors.analyze_document_interactor import (
    AnalyzeDocumentInteractor,
)
from document_scrutiny.interactors.get_ownership_report_interactor import (
    GetOwnershipReportInteractor,
)
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class AnalyzeThreadInteractor:
    def __init__(
        self,
        thread_storage: ScrutinyThreadStorageInterface,
        analyze_document_interactor: AnalyzeDocumentInteractor,
        failure_reporter: FailureReporterInterface,
        ownership_report_interactor: GetOwnershipReportInteractor,
    ):
        self.thread_storage = thread_storage
        self.analyze_document_interactor = analyze_document_interactor
        self.failure_reporter = failure_reporter
        self.ownership_report_interactor = ownership_report_interactor

    def analyze_thread(
        self, request: AnalyzeThreadRequestDTO
    ) -> Iterator[AnalysisEventDTO]:
        analyzed: Set[str] = set()
        # The thread is re-read each pass so a document attached while the run is
        # in flight is still picked up, instead of sitting at `queued` behind a
        # thread that reports itself finished.
        for _ in range(MAX_ANALYSIS_PASSES):
            pending = self._read_pending_documents(
                thread_id=request.thread_id, analyzed=analyzed
            )
            if not pending:
                break
            for document in pending:
                analyzed.add(document.document_id)
                yield from self._analyze_one(
                    thread_id=request.thread_id, document=document
                )

        finished = self.thread_storage.get_thread(thread_id=request.thread_id)
        yield AnalysisEvents.summary(
            ScrutinySummary.summarise(documents=finished.documents)
        )
        yield from self._report_ownership(thread_id=request.thread_id)
        yield AnalysisEvents.done()

    def _report_ownership(self, thread_id: str) -> Iterator[AnalysisEventDTO]:
        """Title is traced once, at the end.

        A bundle's deeds only exist part-way through the run, and a chain read before
        the last one is in would report a break that is really an unfinished read.
        """
        try:
            report = self.ownership_report_interactor.get_ownership_report(
                request=OwnershipReportRequestDTO(thread_id=thread_id)
            )
        except GeneratorExit:
            raise
        except Exception as error_raised:
            # The per-document verdicts are already in the officer's hands. Losing the
            # chain must not also cost them the closing `done` that ends the run.
            self.failure_reporter.report(
                message=f"Tracing title for thread {thread_id} failed unexpectedly",
                error=error_raised,
            )
            return
        if not report.deed_count:
            # Nothing registered was attached, so there is no title to trace and
            # nothing worth saying about it.
            return
        yield AnalysisEvents.chain(ownership_report=report)

    def _read_pending_documents(
        self, thread_id: str, analyzed: Set[str]
    ) -> List[DocumentStateDTO]:
        thread = self.thread_storage.get_thread(thread_id=thread_id)
        return [
            document
            for document in thread.documents
            if document.stage != DocumentStage.DONE.value
            and document.document_id not in analyzed
        ]

    def _analyze_one(
        self, thread_id: str, document: DocumentStateDTO
    ) -> Iterator[AnalysisEventDTO]:
        try:
            events = self.analyze_document_interactor.analyze_document(
                request=AnalyzeDocumentRequestDTO(
                    thread_id=thread_id, document_id=document.document_id
                )
            )
            for event in events:
                if event.event_type == AnalysisEventType.DONE.value:
                    continue
                yield event
        except GeneratorExit:
            raise
        except Exception as error_raised:
            # One unreadable document must not cost the officer the rest of the
            # thread, nor the closing summary that tells them where they stand.
            self.failure_reporter.report(
                message=(
                    f"Analysis of document {document.document_id} in thread "
                    f"{thread_id} failed unexpectedly"
                ),
                error=error_raised,
            )
            yield self._unexpected_failure_event(document.filename)

    @staticmethod
    def _unexpected_failure_event(filename: str) -> AnalysisEventDTO:
        return AnalysisEvents.error(
            UNEXPECTED_FAILURE_MESSAGE.format(filename=filename)
        )
