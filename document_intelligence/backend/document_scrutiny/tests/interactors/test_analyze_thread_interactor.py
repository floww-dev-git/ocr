from unittest.mock import create_autospec

import pytest

from document_scrutiny.constants.analysis_constants import AnalysisEventType
from document_scrutiny.constants.enums import DocumentStage, ThreadStatus
from document_scrutiny.domain.analysis_events import AnalysisEvents
from document_scrutiny.dtos.analysis_dtos import AnalyzeThreadRequestDTO
from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO
from document_scrutiny.tests.conftest import CLEAN_APPLICATION_ID, ScrutinyStorageMock
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    DocumentStateDTOFactory,
)

THREAD_ID = "thread_1"


class TestAnalyzeThreadInteractor(ScrutinyStorageMock):
    @pytest.fixture
    def analyze_document_interactor(self):
        from document_scrutiny.interactors.analyze_document_interactor import (
            AnalyzeDocumentInteractor,
        )

        return create_autospec(AnalyzeDocumentInteractor)

    @pytest.fixture
    def failure_reporter(self):
        from document_scrutiny.adapters.failure_reporter_interface import (
            FailureReporterInterface,
        )

        return create_autospec(FailureReporterInterface)

    @pytest.fixture
    def ownership_report_interactor(self, thread_storage):
        """The real one, over the same mocked storage: a thread holding no deeds must
        genuinely produce no chain frame, which is behaviour worth exercising."""
        from document_scrutiny.interactors.get_ownership_report_interactor import (
            GetOwnershipReportInteractor,
        )

        return GetOwnershipReportInteractor(thread_storage=thread_storage)

    @pytest.fixture
    def interactor(
        self,
        thread_storage,
        analyze_document_interactor,
        failure_reporter,
        ownership_report_interactor,
    ):
        from document_scrutiny.interactors.analyze_thread_interactor import (
            AnalyzeThreadInteractor,
        )

        return AnalyzeThreadInteractor(
            thread_storage=thread_storage,
            analyze_document_interactor=analyze_document_interactor,
            failure_reporter=failure_reporter,
            ownership_report_interactor=ownership_report_interactor,
        )

    def _thread_with(self, *documents) -> ScrutinyThreadDTO:
        return ScrutinyThreadDTO(
            thread_id=THREAD_ID,
            application_id=CLEAN_APPLICATION_ID,
            documents=documents,
        )

    def _run(self, interactor):
        return list(
            interactor.analyze_thread(
                request=AnalyzeThreadRequestDTO(thread_id=THREAD_ID)
            )
        )

    def test_a_thread_with_nothing_attached_still_closes_properly(
        self, interactor, thread_storage, analyze_document_interactor
    ):
        # Arrange
        thread_storage.get_thread.return_value = self._thread_with()

        # Act
        events = self._run(interactor)

        # Assert
        assert [event.event_type for event in events] == [
            AnalysisEventType.SUMMARY.value,
            AnalysisEventType.DONE.value,
        ]
        assert events[0].summary.thread_status == ThreadStatus.NEW.value
        analyze_document_interactor.analyze_document.assert_not_called()

    def test_a_document_already_read_is_not_read_again(
        self, interactor, thread_storage, analyze_document_interactor
    ):
        # Arrange
        finished = DocumentStateDTOFactory(stage=DocumentStage.DONE.value)
        thread_storage.get_thread.return_value = self._thread_with(finished)

        # Act
        self._run(interactor)

        # Assert
        analyze_document_interactor.analyze_document.assert_not_called()

    def test_each_queued_document_is_analyzed_once(
        self, interactor, thread_storage, analyze_document_interactor
    ):
        # Arrange
        first = DocumentStateDTOFactory(
            document_id="document_1", stage=DocumentStage.QUEUED.value
        )
        second = DocumentStateDTOFactory(
            document_id="document_2", stage=DocumentStage.QUEUED.value
        )
        thread_storage.get_thread.return_value = self._thread_with(first, second)
        analyze_document_interactor.analyze_document.return_value = iter(())

        # Act
        self._run(interactor)

        # Assert
        analyzed = [
            call.kwargs["request"].document_id
            for call in analyze_document_interactor.analyze_document.call_args_list
        ]
        assert analyzed == ["document_1", "document_2"]

    def test_the_stream_ends_with_one_summary_and_one_done(
        self, interactor, thread_storage, analyze_document_interactor
    ):
        # Arrange — a per-document done must not leak into the thread stream
        document = DocumentStateDTOFactory(stage=DocumentStage.QUEUED.value)
        thread_storage.get_thread.return_value = self._thread_with(document)
        analyze_document_interactor.analyze_document.return_value = iter(
            (AnalysisEvents.document(document), AnalysisEvents.done())
        )

        # Act
        events = self._run(interactor)

        # Assert
        event_types = [event.event_type for event in events]
        assert event_types.count(AnalysisEventType.DONE.value) == 1
        assert event_types.count(AnalysisEventType.SUMMARY.value) == 1
        assert event_types[-2:] == [
            AnalysisEventType.SUMMARY.value,
            AnalysisEventType.DONE.value,
        ]

    def test_an_error_from_one_document_still_reaches_the_summary(
        self, interactor, thread_storage, analyze_document_interactor
    ):
        # Arrange
        document = DocumentStateDTOFactory(stage=DocumentStage.QUEUED.value)
        thread_storage.get_thread.return_value = self._thread_with(document)
        analyze_document_interactor.analyze_document.return_value = iter(
            (AnalysisEvents.error("could not be read"),)
        )

        # Act
        events = self._run(interactor)

        # Assert
        assert [event.event_type for event in events] == [
            AnalysisEventType.ERROR.value,
            AnalysisEventType.SUMMARY.value,
            AnalysisEventType.DONE.value,
        ]

    def test_the_summary_describes_the_finished_state_not_the_starting_one(
        self, interactor, thread_storage, analyze_document_interactor
    ):
        # Arrange — the thread as it was before the run, then as the run left it
        queued = DocumentStateDTOFactory(stage=DocumentStage.QUEUED.value)
        finished = DocumentStateDTOFactory(
            document_id=queued.document_id,
            stage=DocumentStage.DONE.value,
            confirmed=True,
        )
        thread_storage.get_thread.side_effect = [
            self._thread_with(queued),
            self._thread_with(finished),
            self._thread_with(finished),
            # once more for the closing ownership pass
            self._thread_with(finished),
        ]
        analyze_document_interactor.analyze_document.return_value = iter(())

        # Act
        events = self._run(interactor)

        # Assert
        summary = next(
            event.summary
            for event in events
            if event.event_type == AnalysisEventType.SUMMARY.value
        )
        assert summary.confirmed_document_count == 1
        assert summary.thread_status == ThreadStatus.CLEAR.value

    def test_a_document_attached_while_the_run_is_in_flight_is_still_read(
        self, interactor, thread_storage, analyze_document_interactor
    ):
        # Arrange
        first = DocumentStateDTOFactory(stage=DocumentStage.QUEUED.value)
        late_arrival = DocumentStateDTOFactory(stage=DocumentStage.QUEUED.value)
        thread_storage.get_thread.side_effect = [
            self._thread_with(first),
            self._thread_with(first, late_arrival),
            self._thread_with(first, late_arrival),
            self._thread_with(first, late_arrival),
            # once more for the closing ownership pass
            self._thread_with(first, late_arrival),
        ]
        analyze_document_interactor.analyze_document.return_value = iter(())

        # Act
        self._run(interactor)

        # Assert
        analyzed = [
            call.kwargs["request"].document_id
            for call in analyze_document_interactor.analyze_document.call_args_list
        ]
        assert analyzed == [first.document_id, late_arrival.document_id]

    def test_one_document_failing_does_not_cost_the_officer_the_rest(
        self, interactor, thread_storage, analyze_document_interactor
    ):
        # Arrange
        broken = DocumentStateDTOFactory(
            stage=DocumentStage.QUEUED.value, filename="broken.pdf"
        )
        sound = DocumentStateDTOFactory(stage=DocumentStage.QUEUED.value)
        thread_storage.get_thread.return_value = self._thread_with(broken, sound)

        def explode(request):
            if request.document_id == broken.document_id:
                raise RuntimeError("reader blew up")
            return iter(())

        analyze_document_interactor.analyze_document.side_effect = explode

        # Act
        events = self._run(interactor)

        # Assert
        assert [event.event_type for event in events] == [
            AnalysisEventType.ERROR.value,
            AnalysisEventType.SUMMARY.value,
            AnalysisEventType.DONE.value,
        ]
        assert "broken.pdf" in events[0].message
        assert analyze_document_interactor.analyze_document.call_count == 2

    def test_a_fault_hidden_from_the_officer_is_still_reported_to_developers(
        self, interactor, thread_storage, analyze_document_interactor, failure_reporter
    ):
        # Arrange — swallowing an exception to save the run must not lose it
        document = DocumentStateDTOFactory(stage=DocumentStage.QUEUED.value)
        thread_storage.get_thread.return_value = self._thread_with(document)
        blew_up = RuntimeError("reader blew up")
        analyze_document_interactor.analyze_document.side_effect = blew_up

        # Act
        self._run(interactor)

        # Assert
        reported = failure_reporter.report.call_args.kwargs
        assert reported["error"] is blew_up
        assert document.document_id in reported["message"]

    def test_an_unexpected_failure_does_not_leak_its_text_to_the_officer(
        self, interactor, thread_storage, analyze_document_interactor
    ):
        # Arrange
        document = DocumentStateDTOFactory(stage=DocumentStage.QUEUED.value)
        thread_storage.get_thread.return_value = self._thread_with(document)
        analyze_document_interactor.analyze_document.side_effect = RuntimeError(
            "psycopg2.OperationalError: password=hunter2"
        )

        # Act
        events = self._run(interactor)

        # Assert
        assert "hunter2" not in events[0].message
        assert "psycopg2" not in events[0].message
