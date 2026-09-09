import dataclasses
from typing import Generator, Iterator, Optional, Tuple

from document_catalog.app_interfaces.catalog_service_interface import (
    CatalogServiceInterface,
)
from document_catalog.dtos.catalog_dtos import ApplicationDTO, DocumentTypeDTO
from document_extraction.app_interfaces.extraction_service_interface import (
    ExtractionServiceInterface,
)
from document_extraction.dtos.extraction_dtos import (
    DocumentClassificationDTO,
    ExtractDocumentRequestDTO,
)
from document_extraction.exceptions.extraction_exceptions import ExtractionFailed
from document_scrutiny.constants.analysis_constants import (
    UNREADABLE_DOCUMENT_MESSAGE,
    AnalysisStep,
)
from document_scrutiny.constants.enums import DocumentStage
from document_scrutiny.domain.analysis_events import AnalysisEvents
from document_scrutiny.domain.cross_document_consistency_check import (
    CrossDocumentConsistencyCheck,
    SiblingName as CrossDocumentSiblingName,
)
from document_scrutiny.domain.document_progress import DocumentProgress
from document_scrutiny.domain.unsupported_type_check import UnsupportedTypeCheck
from document_scrutiny.dtos.analysis_dtos import (
    AnalysisEventDTO,
    AnalyzeDocumentRequestDTO,
)
from document_scrutiny.dtos.bundle_dtos import SegmentBundleRequestDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.run_checks_dtos import RunDocumentChecksRequestDTO
from document_scrutiny.dtos.thread_dtos import DocumentLookupDTO, ScrutinyThreadDTO
from document_scrutiny.interactors.document_run_record import DocumentRunRecord
from document_scrutiny.interactors.issuer_consultation import IssuerConsultation
from document_scrutiny.interactors.run_document_checks_interactor import (
    RunDocumentChecksInteractor,
)
from document_scrutiny.interactors.segment_bundle_interactor import (
    SegmentBundleInteractor,
)
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)

EXTRACTION_SOURCE = "upload"


class AnalyzeDocumentInteractor:
    def __init__(
        self,
        thread_storage: ScrutinyThreadStorageInterface,
        catalog_service: CatalogServiceInterface,
        extraction_service: ExtractionServiceInterface,
        consultation: IssuerConsultation,
        scrutiny_today: str,
        segment_bundle_interactor: SegmentBundleInteractor,
    ):
        self.thread_storage = thread_storage
        self.catalog_service = catalog_service
        self.extraction_service = extraction_service
        self.consultation = consultation
        self.scrutiny_today = scrutiny_today
        self.segment_bundle_interactor = segment_bundle_interactor
        self.run_record = DocumentRunRecord(thread_storage=thread_storage)

    def analyze_document(
        self, request: AnalyzeDocumentRequestDTO
    ) -> Iterator[AnalysisEventDTO]:
        try:
            yield from self._analyze(request=request)
        finally:
            # A closed browser tab, a navigation, or a reconnect stops this
            # generator wherever it stands. Without settling the document here it
            # keeps a mid-run stage forever, and the thread reports `running`
            # behind a spinner with nothing left driving it.
            self.run_record.settle_if_abandoned(
                thread_id=request.thread_id, document_id=request.document_id
            )

    def _analyze(
        self, request: AnalyzeDocumentRequestDTO
    ) -> Iterator[AnalysisEventDTO]:
        thread = self.thread_storage.get_thread(thread_id=request.thread_id)
        document = self.thread_storage.get_document(
            lookup=DocumentLookupDTO(
                thread_id=request.thread_id, document_id=request.document_id
            )
        )
        extract_request = self._build_extract_request(thread=thread, document=document)

        classification, document = yield from self._identify(
            thread_id=request.thread_id,
            document=document,
            extract_request=extract_request,
        )
        if classification is None:
            return
        if classification.is_bundle:
            # The file holds several registered documents. Each becomes a document
            # of its own and is read on the next pass; there is nothing to read off
            # the bundle itself.
            yield from self._segment(
                thread_id=request.thread_id,
                document=document,
                classification=classification,
            )
            return
        if not classification.implemented:
            yield from self._report_unsupported(
                thread_id=request.thread_id,
                document=document,
                classification=classification,
            )
            return

        document = yield from self._extract(
            thread_id=request.thread_id,
            document=document,
            # Reading needs to know what it decided this is, so the right schema
            # and prompt are used. Classification could not say yet.
            extract_request=dataclasses.replace(
                extract_request, document_type_id=classification.document_type_id
            ),
        )
        if document is None:
            return

        document_type, application = self._read_reference_data(
            document_type_id=classification.document_type_id, thread=thread
        )
        document = yield from self._run_checks(
            thread_id=request.thread_id,
            document=document,
            document_type=document_type,
            application=application,
        )
        document = yield from self._verify(
            thread_id=request.thread_id,
            thread=thread,
            document=document,
            document_type=document_type,
        )
        yield from self._cross_check(
            thread_id=request.thread_id, document=document
        )

    def _identify(
        self,
        thread_id: str,
        document: DocumentStateDTO,
        extract_request: ExtractDocumentRequestDTO,
    ) -> Generator[
        AnalysisEventDTO, None, Tuple[Optional[DocumentClassificationDTO], DocumentStateDTO]
    ]:
        yield AnalysisEvents.step_running(AnalysisStep.IDENTIFY)
        classification = self._established_classification(document=document)
        if classification is None:
            try:
                classification = self.extraction_service.classify_document(
                    request=extract_request
                )
            except ExtractionFailed:
                yield self._unreadable_event(document)
                return None, document
        identified = self._save(
            thread_id=thread_id,
            document=DocumentProgress.with_classification(
                document=document, classification=classification
            ),
        )
        yield AnalysisEvents.document(identified)
        yield AnalysisEvents.step_done(AnalysisStep.IDENTIFY)
        return classification, identified

    @staticmethod
    def _established_classification(
        document: DocumentStateDTO,
    ) -> Optional[DocumentClassificationDTO]:
        """What a document carved out of a bundle already is.

        The inventory pass could see this deed sitting behind a later one in the
        same file, which is how it knew to call it a link document. Asking the model
        again about the slice alone would throw that away and read every deed in the
        bundle as the current one.
        """
        if document.parent_document_id is None or document.document_type_id is None:
            return None
        return DocumentClassificationDTO(
            document_type_id=document.document_type_id,
            document_type_label=document.document_type_label,
            type_confidence=document.type_confidence,
            implemented=document.implemented,
            page_count=document.page_count,
            total_page_count=document.page_count,
        )

    def _segment(
        self,
        thread_id: str,
        document: DocumentStateDTO,
        classification: DocumentClassificationDTO,
    ) -> Iterator[AnalysisEventDTO]:
        segmentation = self.segment_bundle_interactor.segment_bundle(
            request=SegmentBundleRequestDTO(
                thread_id=thread_id,
                document_id=document.document_id,
                segments=classification.segments,
            )
        )
        yield AnalysisEvents.document(segmentation.parent)
        for child in segmentation.children:
            yield AnalysisEvents.document(child)

    def _report_unsupported(
        self,
        thread_id: str,
        document: DocumentStateDTO,
        classification: DocumentClassificationDTO,
    ) -> Iterator[AnalysisEventDTO]:
        unsupported = self._record_unsupported(
            thread_id=thread_id, document=document, classification=classification
        )
        yield AnalysisEvents.document(unsupported)
        yield AnalysisEvents.error(
            UnsupportedTypeCheck.build_message(
                document_type_id=classification.document_type_id,
                document_type_label=classification.document_type_label,
                filename=document.filename,
            )
        )

    def _extract(
        self,
        thread_id: str,
        document: DocumentStateDTO,
        extract_request: ExtractDocumentRequestDTO,
    ) -> Generator[AnalysisEventDTO, None, Optional[DocumentStateDTO]]:
        yield AnalysisEvents.step_running(AnalysisStep.EXTRACT)
        try:
            record = self.extraction_service.extract_document_record(
                request=extract_request
            )
        except ExtractionFailed:
            yield self._unreadable_event(document)
            return None
        read = self._save(
            thread_id=thread_id,
            document=DocumentProgress.with_read(document=document, record=record),
        )
        yield AnalysisEvents.document(read)
        yield AnalysisEvents.step_done(AnalysisStep.EXTRACT)
        return read

    def _run_checks(
        self,
        thread_id: str,
        document: DocumentStateDTO,
        document_type: DocumentTypeDTO,
        application: ApplicationDTO,
    ) -> Generator[AnalysisEventDTO, None, DocumentStateDTO]:
        yield AnalysisEvents.step_running(AnalysisStep.CHECKS)
        checks = RunDocumentChecksInteractor().run_checks(
            request=RunDocumentChecksRequestDTO(
                document_id=document.document_id,
                document_type=document_type,
                application=application,
                scrutiny_today=self.scrutiny_today,
                field_values=document.field_values,
                structure_findings=document.structure_findings,
                qr_fields=document.qr_fields,
                quality=document.quality,
            )
        )
        checked = self._save(
            thread_id=thread_id,
            document=DocumentProgress.with_stage(
                document=document,
                stage=DocumentStage.CHECKING.value,
                checks=tuple(checks),
            ),
        )
        yield AnalysisEvents.document(checked)
        yield AnalysisEvents.step_done(AnalysisStep.CHECKS, check_count=len(checks))
        return checked

    def _verify(
        self,
        thread_id: str,
        thread: ScrutinyThreadDTO,
        document: DocumentStateDTO,
        document_type: DocumentTypeDTO,
    ) -> Generator[AnalysisEventDTO, None, DocumentStateDTO]:
        yield AnalysisEvents.step_running(AnalysisStep.VERIFY)
        verifying = self._save(
            thread_id=thread_id,
            document=DocumentProgress.with_stage(
                document=document, stage=DocumentStage.VERIFYING.value
            ),
        )
        issuer_check = self.consultation.consult(
            thread=thread, document=verifying, document_type=document_type
        )
        verified = self._save(
            thread_id=thread_id,
            document=DocumentProgress.with_stage(
                document=verifying,
                stage=DocumentStage.DONE.value,
                checks=verifying.checks + (issuer_check,),
            ),
        )
        yield AnalysisEvents.document(verified)
        yield AnalysisEvents.step_done(AnalysisStep.VERIFY)
        return verified

    def _cross_check(
        self, thread_id: str, document: DocumentStateDTO
    ) -> Iterator[AnalysisEventDTO]:
        """Reconcile this document's identity against its siblings on the file.

        Runs after the document has settled, and re-reads the thread so it sees the
        other documents as they now stand. It is the one check that compares
        documents to each other rather than to the application, so it lives here at
        the thread level rather than in the per-document check engine. Absent when
        there is nothing to compare against, so nothing changes for a lone document.
        """
        siblings = self._sibling_names(thread_id=thread_id, document=document)
        cross_check = CrossDocumentConsistencyCheck.build(
            document_id=document.document_id,
            name=self._read_name(document),
            siblings=siblings,
        )
        if cross_check is None:
            return
        reconciled = self._save(
            thread_id=thread_id,
            document=DocumentProgress.with_stage(
                document=document,
                stage=DocumentStage.DONE.value,
                checks=document.checks + (cross_check,),
            ),
        )
        yield AnalysisEvents.document(reconciled)

    def _sibling_names(
        self, thread_id: str, document: DocumentStateDTO
    ) -> Tuple[CrossDocumentSiblingName, ...]:
        thread = self.thread_storage.get_thread(thread_id=thread_id)
        siblings = []
        for other in thread.documents:
            if other.document_id == document.document_id:
                continue
            if other.stage != DocumentStage.DONE.value:
                continue
            name = self._read_name(other)
            if name is None:
                continue
            siblings.append(
                CrossDocumentSiblingName(
                    document_type_label=other.document_type_label, name=name
                )
            )
        return tuple(siblings)

    @staticmethod
    def _read_name(document: DocumentStateDTO) -> Optional[str]:
        for field_value in document.field_values:
            if field_value.key == "name":
                value = str(field_value.value or "").strip()
                return value or None
        return None

    @staticmethod
    def _unreadable_event(document: DocumentStateDTO) -> AnalysisEventDTO:
        return AnalysisEvents.error(
            UNREADABLE_DOCUMENT_MESSAGE.format(filename=document.filename)
        )

    def _build_extract_request(
        self, thread: ScrutinyThreadDTO, document: DocumentStateDTO
    ) -> ExtractDocumentRequestDTO:
        file_path = self.thread_storage.get_document_file_path(
            lookup=DocumentLookupDTO(
                thread_id=thread.thread_id, document_id=document.document_id
            )
        )
        return ExtractDocumentRequestDTO(
            filename=document.filename,
            application_id=thread.application_id,
            source=EXTRACTION_SOURCE,
            file_path=file_path,
            # A document carved out of a bundle names the pages it occupies in its
            # parent's file, which is the only file either of them has.
            page_start=document.page_start,
            page_end=document.page_end,
        )

    def _read_reference_data(
        self, document_type_id: str, thread: ScrutinyThreadDTO
    ) -> Tuple[DocumentTypeDTO, ApplicationDTO]:
        return (
            self.catalog_service.get_document_type(document_type_id=document_type_id),
            self.catalog_service.get_application(
                application_id=thread.application_id
            ),
        )

    def _record_unsupported(
        self,
        thread_id: str,
        document: DocumentStateDTO,
        classification: DocumentClassificationDTO,
    ) -> DocumentStateDTO:
        unsupported = UnsupportedTypeCheck.build(
            document_id=document.document_id,
            document_type_id=classification.document_type_id,
            document_type_label=classification.document_type_label,
        )
        return self._save(
            thread_id=thread_id,
            document=DocumentProgress.with_stage(
                document=document,
                stage=DocumentStage.DONE.value,
                checks=(unsupported,),
            ),
        )

    def _save(self, thread_id: str, document: DocumentStateDTO) -> DocumentStateDTO:
        return self.run_record.save(thread_id=thread_id, document=document)
