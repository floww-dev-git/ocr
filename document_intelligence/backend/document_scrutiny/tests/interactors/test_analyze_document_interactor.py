import dataclasses
from unittest.mock import create_autospec

import pytest

from document_catalog.storages.reference_data.identity_document_specs import (
    AADHAAR_SPEC,
    PAN_SPEC,
)
from document_extraction.dtos.extraction_dtos import DocumentClassificationDTO
from document_extraction.dtos.document_record_dtos import (
    FieldBoxDTO,
    FieldReadDTO,
    DocumentRecordDTO,
)
from document_extraction.exceptions.extraction_exceptions import ExtractionFailed
from document_scrutiny.constants.analysis_constants import (
    AnalysisEventType,
    AnalysisStep,
    StepState,
)
from document_scrutiny.constants.enums import CheckStatus, DocumentStage, DocumentStatus
from document_scrutiny.dtos.analysis_dtos import AnalyzeDocumentRequestDTO
from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO
from document_scrutiny.tests.conftest import (
    SCRUTINY_TODAY,
    CLEAN_APPLICATION_ID,
    MISMATCH_APPLICATION_ID,
    ScrutinyStorageMock,
    wire_document_memory,
)
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    DocumentStateDTOFactory,
)
from document_verification.constants.verification_constants import IssuerOutcome
from document_verification.dtos.verification_dtos import IssuerAnswerDTO

THREAD_ID = "thread_1"
DOCUMENT_ID = "document_1"

CLEAN_READS = (
    FieldReadDTO(key="name", value="SRINIVAS RAO KANDULA", confidence=0.98),
    FieldReadDTO(key="parentName", value="VENKATESWARA RAO KANDULA", confidence=0.96),
    FieldReadDTO(key="dob", value="1979-08-14", confidence=0.99),
    FieldReadDTO(key="pan", value="DQRPK4831L", confidence=0.99),
)
MISMATCH_READS = (
    FieldReadDTO(key="name", value="MOHAMMED IRFAN SIDDIQI", confidence=0.95),
    FieldReadDTO(key="parentName", value="MOHAMMED YOUSUF SIDDIQUI", confidence=0.95),
    FieldReadDTO(key="dob", value="1982-11-27", confidence=0.98),
    FieldReadDTO(key="pan", value="BNMPS7720K", confidence=0.99),
)
ALL_STRUCTURE = {"photo": True, "signature": True, "hologram": True}


def build_document_record(field_reads=CLEAN_READS, structure=None) -> DocumentRecordDTO:
    return DocumentRecordDTO(
        field_reads=field_reads,
        structure_findings=dict(ALL_STRUCTURE if structure is None else structure),
        overall_confidence=0.96,
        low_confidence_fields=(),
        boxes=(
            FieldBoxDTO(field_key="pan", value="DQRPK4831L", page=0, box=(1, 2, 3, 4)),
        ),
        page_count=1,
    )


def build_classification(
    document_type_id: str = "pan", label: str = "PAN", implemented: bool = True
) -> DocumentClassificationDTO:
    return DocumentClassificationDTO(
        document_type_id=document_type_id,
        document_type_label=label,
        type_confidence=0.99,
        implemented=implemented,
        page_count=1,
        total_page_count=1,
    )


class TestAnalyzeDocumentInteractor(ScrutinyStorageMock):
    @pytest.fixture
    def extraction_service(self):
        from document_extraction.app_interfaces.extraction_service_interface import (
            ExtractionServiceInterface,
        )

        return create_autospec(ExtractionServiceInterface)

    @pytest.fixture
    def verification_service(self):
        from document_verification.app_interfaces.verification_service_interface import (
            VerificationServiceInterface,
        )

        return create_autospec(VerificationServiceInterface)

    @pytest.fixture
    def consultation(self, catalog_service, verification_service):
        from document_scrutiny.interactors.issuer_consultation import (
            IssuerConsultation,
        )

        return IssuerConsultation(
            catalog_service=catalog_service,
            verification_service=verification_service,
        )

    @pytest.fixture
    def interactor(
        self,
        thread_storage,
        catalog_service,
        extraction_service,
        consultation,
        segment_bundle_interactor,
    ):
        from document_scrutiny.interactors.analyze_document_interactor import (
            AnalyzeDocumentInteractor,
        )

        return AnalyzeDocumentInteractor(
            thread_storage=thread_storage,
            catalog_service=catalog_service,
            extraction_service=extraction_service,
            consultation=consultation,
            scrutiny_today=SCRUTINY_TODAY,
            segment_bundle_interactor=segment_bundle_interactor,
        )

    @pytest.fixture(autouse=True)
    def queued_document(self, thread_storage):
        document = DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            filename="pan_card.pdf",
            document_type_id=None,
            document_type_label="",
            type_confidence=0.0,
            implemented=False,
            stage=DocumentStage.QUEUED.value,
            status=DocumentStatus.CHECKING.value,
            page_count=0,
        )
        thread_storage.get_thread.return_value = ScrutinyThreadDTO(
            thread_id=THREAD_ID,
            application_id=CLEAN_APPLICATION_ID,
            documents=(document,),
        )
        thread_storage.get_document.return_value = document
        thread_storage.get_document_file_path.return_value = "/uploads/t/x.pdf"
        thread_storage.update_document.side_effect = (
            lambda update_document: update_document.document
        )
        return document

    def _run(self, interactor):
        request = AnalyzeDocumentRequestDTO(
            thread_id=THREAD_ID, document_id=DOCUMENT_ID
        )
        return list(interactor.analyze_document(request=request))

    @staticmethod
    def _steps(events):
        return [
            (event.step, event.step_state)
            for event in events
            if event.event_type == AnalysisEventType.STEP.value
        ]

    @staticmethod
    def _last_document(events):
        documents = [
            event.document
            for event in events
            if event.event_type == AnalysisEventType.DOCUMENT.value
        ]
        return documents[-1]

    def test_a_document_that_cannot_be_read_ends_the_stream_with_an_error(
        self, interactor, extraction_service, verification_service
    ):
        # Arrange
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.side_effect = ExtractionFailed(
            filename="pan_card.pdf", reason="the model returned no readable response"
        )

        # Act
        events = self._run(interactor)

        # Assert
        assert events[-1].event_type == AnalysisEventType.ERROR.value
        assert "pan_card.pdf" in events[-1].message
        verification_service.verify_document.assert_not_called()

    def test_an_unreadable_document_never_leaks_the_underlying_failure_text(
        self, interactor, extraction_service
    ):
        # Arrange
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.side_effect = ExtractionFailed(
            filename="pan_card.pdf", reason="google.genai.errors.ServerError: 500 boom"
        )

        # Act
        events = self._run(interactor)

        # Assert
        assert "google.genai" not in events[-1].message
        assert "500" not in events[-1].message

    def test_a_declared_but_unsupported_type_stops_before_extraction(
        self, interactor, extraction_service, verification_service
    ):
        # Arrange — AC10
        extraction_service.classify_document.return_value = build_classification(
            document_type_id=AADHAAR_SPEC.document_type_id,
            label=AADHAAR_SPEC.label,
            implemented=False,
        )

        # Act
        events = self._run(interactor)

        # Assert
        assert self._steps(events) == [
            (AnalysisStep.IDENTIFY.value, StepState.RUNNING.value),
            (AnalysisStep.IDENTIFY.value, StepState.DONE.value),
        ]
        assert events[-1].event_type == AnalysisEventType.ERROR.value
        assert events[-1].message == "Aadhaar is recognised but not supported in this build."
        extraction_service.extract_document_record.assert_not_called()
        verification_service.verify_document.assert_not_called()

    def test_an_unsupported_document_is_left_finished_not_forever_in_progress(
        self, interactor, extraction_service
    ):
        # Arrange — nothing more will happen to it, so a thread holding only this
        # document must not report itself as still running
        extraction_service.classify_document.return_value = build_classification(
            document_type_id=AADHAAR_SPEC.document_type_id,
            label=AADHAAR_SPEC.label,
            implemented=False,
        )

        # Act
        events = self._run(interactor)

        # Assert
        document = self._last_document(events)
        assert document.stage == DocumentStage.DONE.value
        assert document.status == DocumentStatus.ATTENTION.value

    def test_an_unsupported_document_records_a_warning_the_officer_must_resolve(
        self, interactor, extraction_service
    ):
        # Arrange — the stream's error frame is transient; the worklist needs a record
        extraction_service.classify_document.return_value = build_classification(
            document_type_id=AADHAAR_SPEC.document_type_id,
            label=AADHAAR_SPEC.label,
            implemented=False,
        )

        # Act
        events = self._run(interactor)

        # Assert
        document = self._last_document(events)
        assert len(document.checks) == 1
        unsupported = document.checks[0]
        assert unsupported.check_id == f"{DOCUMENT_ID}:supported"
        assert unsupported.status == CheckStatus.WARN.value
        assert unsupported.title == "Aadhaar is not supported in this build"

    def test_a_document_nobody_could_classify_stops_after_identifying(
        self, interactor, extraction_service
    ):
        # Arrange
        extraction_service.classify_document.return_value = build_classification(
            document_type_id="unknown", label="Unknown document", implemented=False
        )

        # Act
        events = self._run(interactor)

        # Assert
        assert events[-1].event_type == AnalysisEventType.ERROR.value
        extraction_service.extract_document_record.assert_not_called()

    def test_a_document_nobody_could_classify_says_so_in_its_own_words(
        self, interactor, extraction_service
    ):
        # Arrange — "Unknown document is not supported" would be nonsense
        extraction_service.classify_document.return_value = build_classification(
            document_type_id="unknown", label="Unknown document", implemented=False
        )

        # Act
        events = self._run(interactor)

        # Assert
        assert events[-1].message == (
            "We could not tell what pan_card.pdf is. Check the scan, or attach a "
            "clearer copy."
        )
        assert self._last_document(events).checks[0].title == (
            "Document type could not be established"
        )

    def test_an_unreachable_issuer_still_finishes_every_step(
        self, interactor, extraction_service, verification_service
    ):
        # Arrange — AC7
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record()
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.UNREACHABLE.value,
            latency_ms=3000,
            unreachable_reason="timed_out",
        )

        # Act
        events = self._run(interactor)

        # Assert
        assert self._steps(events)[-1] == (
            AnalysisStep.VERIFY.value,
            StepState.DONE.value,
        )
        assert events[-1].event_type != AnalysisEventType.ERROR.value
        document = self._last_document(events)
        assert document.status == DocumentStatus.UNAVAILABLE.value

    def test_the_four_steps_arrive_in_order(
        self, interactor, extraction_service, verification_service
    ):
        # Arrange
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record()
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.CONFIRMED.value, latency_ms=912
        )

        # Act
        events = self._run(interactor)

        # Assert
        assert self._steps(events) == [
            (AnalysisStep.IDENTIFY.value, StepState.RUNNING.value),
            (AnalysisStep.IDENTIFY.value, StepState.DONE.value),
            (AnalysisStep.EXTRACT.value, StepState.RUNNING.value),
            (AnalysisStep.EXTRACT.value, StepState.DONE.value),
            (AnalysisStep.CHECKS.value, StepState.RUNNING.value),
            (AnalysisStep.CHECKS.value, StepState.DONE.value),
            (AnalysisStep.VERIFY.value, StepState.RUNNING.value),
            (AnalysisStep.VERIFY.value, StepState.DONE.value),
        ]

    def test_the_checks_step_reports_how_many_checks_it_produced(
        self, interactor, extraction_service, verification_service
    ):
        # Arrange
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record()
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.CONFIRMED.value, latency_ms=912
        )

        # Act
        events = self._run(interactor)

        # Assert
        checks_done = next(
            event
            for event in events
            if event.event_type == AnalysisEventType.STEP.value
            and event.step == AnalysisStep.CHECKS.value
            and event.step_state == StepState.DONE.value
        )
        assert checks_done.check_count == 9

    def test_a_clean_pan_finishes_verified_with_ten_passing_checks(
        self, interactor, extraction_service, verification_service
    ):
        # Arrange — AC1
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record()
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.CONFIRMED.value, latency_ms=912
        )

        # Act
        events = self._run(interactor)

        # Assert
        document = self._last_document(events)
        assert document.stage == DocumentStage.DONE.value
        assert document.status == DocumentStatus.VERIFIED.value
        # Eight field/structure checks, the intrinsic date-of-birth consistency
        # check, and the issuer answer.
        assert len(document.checks) == 10
        assert {check.status for check in document.checks} == {CheckStatus.PASS.value}

    def test_the_seeded_mismatch_finishes_needing_attention(
        self, interactor, extraction_service, verification_service, thread_storage
    ):
        # Arrange — AC2 and AC6 together
        thread_storage.get_thread.return_value = dataclasses.replace(
            thread_storage.get_thread.return_value,
            application_id=MISMATCH_APPLICATION_ID,
        )
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record(
            field_reads=MISMATCH_READS
        )
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.PARTIAL_MATCH.value,
            latency_ms=964,
            disagreeing_fields=("name",),
            response_payload={"status": "VALID", "nameMatch": False},
        )

        # Act
        events = self._run(interactor)

        # Assert
        document = self._last_document(events)
        assert document.status == DocumentStatus.ATTENTION.value
        warned = [
            check.check_id
            for check in document.checks
            if check.status == CheckStatus.WARN.value
        ]
        assert warned == [f"{DOCUMENT_ID}:name", f"{DOCUMENT_ID}:issuer"]

    def test_the_issuer_is_asked_with_the_demographics_that_were_read(
        self, interactor, extraction_service, verification_service
    ):
        # Arrange
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record()
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.CONFIRMED.value, latency_ms=912
        )

        # Act
        self._run(interactor)

        # Assert
        verify_request = verification_service.verify_document.call_args.kwargs["request"]
        assert verify_request.lookup_values["pan"] == "DQRPK4831L"
        assert verify_request.lookup_values["name"] == "SRINIVAS RAO KANDULA"
        assert verify_request.lookup_values["dob"] == "1979-08-14"
        assert verify_request.issuer_service_id == PAN_SPEC.issuer_service_id

    def test_a_forced_service_outcome_on_the_thread_reaches_the_issuer(
        self, interactor, extraction_service, verification_service, thread_storage
    ):
        # Arrange
        thread_storage.get_thread.return_value = dataclasses.replace(
            thread_storage.get_thread.return_value,
            service_overrides={"itd_pan": "timeout"},
        )
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record()
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.UNREACHABLE.value,
            latency_ms=3000,
            unreachable_reason="timed_out",
        )

        # Act
        self._run(interactor)

        # Assert
        verify_request = verification_service.verify_document.call_args.kwargs["request"]
        assert verify_request.service_override == "timeout"

    def test_the_document_is_recorded_at_every_stage_it_reaches(
        self, interactor, extraction_service, verification_service, thread_storage
    ):
        # Arrange
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record()
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.CONFIRMED.value, latency_ms=912
        )

        # Act
        self._run(interactor)

        # Assert
        recorded_stages = [
            call.kwargs["update_document"].document.stage
            for call in thread_storage.update_document.call_args_list
        ]
        assert recorded_stages == [
            DocumentStage.IDENTIFYING.value,
            DocumentStage.EXTRACTING.value,
            DocumentStage.CHECKING.value,
            DocumentStage.VERIFYING.value,
            DocumentStage.DONE.value,
        ]

    def test_the_read_fields_and_structure_reach_the_document(
        self, interactor, extraction_service, verification_service
    ):
        # Arrange
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record(
            structure={"photo": True, "signature": True, "hologram": False}
        )
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.CONFIRMED.value, latency_ms=912
        )

        # Act
        events = self._run(interactor)

        # Assert
        document = self._last_document(events)
        assert {value.key: value.value for value in document.field_values} == {
            "name": "SRINIVAS RAO KANDULA",
            "parentName": "VENKATESWARA RAO KANDULA",
            "dob": "1979-08-14",
            "pan": "DQRPK4831L",
        }
        assert document.structure_findings["hologram"] is False
        assert document.page_count == 1
        assert document.document_type_label == "PAN"
        assert document.type_confidence == 0.99

    def test_the_stored_file_is_handed_to_extraction_for_a_real_read(
        self, interactor, extraction_service, verification_service
    ):
        # Arrange
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record()
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.CONFIRMED.value, latency_ms=912
        )

        # Act
        self._run(interactor)

        # Assert
        classify_request = extraction_service.classify_document.call_args.kwargs["request"]
        assert classify_request.file_path == "/uploads/t/x.pdf"
        assert classify_request.filename == "pan_card.pdf"
        assert classify_request.application_id == CLEAN_APPLICATION_ID


class TestAnAbandonedRun(ScrutinyStorageMock):
    """A closed browser tab stops the generator wherever it stands. The document
    must not keep a mid-run stage, or the thread reports `running` forever behind
    a spinner with nothing driving it (the general form of the bug ADR-006 D6
    fixed for unsupported documents)."""

    @pytest.fixture
    def extraction_service(self):
        from document_extraction.app_interfaces.extraction_service_interface import (
            ExtractionServiceInterface,
        )

        return create_autospec(ExtractionServiceInterface)

    @pytest.fixture
    def verification_service(self):
        from document_verification.app_interfaces.verification_service_interface import (
            VerificationServiceInterface,
        )

        return create_autospec(VerificationServiceInterface)

    @pytest.fixture
    def consultation(self, catalog_service, verification_service):
        from document_scrutiny.interactors.issuer_consultation import (
            IssuerConsultation,
        )

        return IssuerConsultation(
            catalog_service=catalog_service,
            verification_service=verification_service,
        )

    @pytest.fixture
    def interactor(
        self,
        thread_storage,
        catalog_service,
        extraction_service,
        consultation,
        segment_bundle_interactor,
    ):
        from document_scrutiny.interactors.analyze_document_interactor import (
            AnalyzeDocumentInteractor,
        )

        return AnalyzeDocumentInteractor(
            thread_storage=thread_storage,
            catalog_service=catalog_service,
            extraction_service=extraction_service,
            consultation=consultation,
            scrutiny_today=SCRUTINY_TODAY,
            segment_bundle_interactor=segment_bundle_interactor,
        )

    def test_abandoning_the_run_settles_the_document_with_a_warning(
        self, interactor, thread_storage, extraction_service
    ):
        # Arrange
        from document_scrutiny.constants.analysis_constants import (
            ABANDONED_RUN_CHECK_KEY,
        )

        queued = DocumentStateDTOFactory(
            document_id=DOCUMENT_ID, stage=DocumentStage.QUEUED.value, checks=()
        )
        state = wire_document_memory(
            thread_storage=thread_storage,
            documents=(queued,),
            application_id=MISMATCH_APPLICATION_ID,
        )
        thread_storage.get_document_file_path.return_value = "/tmp/pan.jpg"
        extraction_service.classify_document.return_value = build_classification()

        # Act — take the first frame, then walk away
        events = interactor.analyze_document(
            request=AnalyzeDocumentRequestDTO(
                thread_id=THREAD_ID, document_id=DOCUMENT_ID
            )
        )
        next(events)
        next(events)
        assert state[DOCUMENT_ID].stage == DocumentStage.IDENTIFYING.value
        events.close()

        # Assert
        settled = state[DOCUMENT_ID]
        assert settled.stage == DocumentStage.DONE.value
        assert [check.check_id.split(":")[-1] for check in settled.checks] == [
            ABANDONED_RUN_CHECK_KEY
        ]
        assert settled.status != DocumentStatus.CHECKING.value

    def test_a_run_that_finished_is_not_marked_abandoned(
        self, interactor, thread_storage, extraction_service, verification_service
    ):
        # Arrange
        from document_scrutiny.constants.analysis_constants import (
            ABANDONED_RUN_CHECK_KEY,
        )

        queued = DocumentStateDTOFactory(
            document_id=DOCUMENT_ID, stage=DocumentStage.QUEUED.value, checks=()
        )
        state = wire_document_memory(
            thread_storage=thread_storage,
            documents=(queued,),
            application_id=MISMATCH_APPLICATION_ID,
        )
        thread_storage.get_document_file_path.return_value = "/tmp/pan.jpg"
        extraction_service.classify_document.return_value = build_classification()
        extraction_service.extract_document_record.return_value = build_document_record(
            field_reads=MISMATCH_READS
        )
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome="confirmed", latency_ms=500
        )

        # Act
        list(
            interactor.analyze_document(
                request=AnalyzeDocumentRequestDTO(
                    thread_id=THREAD_ID, document_id=DOCUMENT_ID
                )
            )
        )

        # Assert
        settled = state[DOCUMENT_ID]
        assert settled.stage == DocumentStage.DONE.value
        assert ABANDONED_RUN_CHECK_KEY not in {
            check.check_id.split(":")[-1] for check in settled.checks
        }
