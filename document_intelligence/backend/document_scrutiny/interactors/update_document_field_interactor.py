import dataclasses
from typing import Tuple

from document_catalog.app_interfaces.catalog_service_interface import (
    CatalogServiceInterface,
)

from document_scrutiny.domain.check_reconciliation import CheckReconciliation
from document_scrutiny.domain.deed_record_edit import DeedRecordEdit
from document_scrutiny.domain.document_progress import DocumentProgress
from document_scrutiny.domain.officer_action_guard import OfficerActionGuard
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.officer_action_dtos import (
    DocumentChangeDTO,
    UpdateDocumentFieldRequestDTO,
)
from document_scrutiny.dtos.run_checks_dtos import RunDocumentChecksRequestDTO
from document_scrutiny.dtos.thread_dtos import DocumentLookupDTO
from document_scrutiny.exceptions.scrutiny_exceptions import DocumentFieldNotFound
from document_scrutiny.interactors.run_document_checks_interactor import (
    RunDocumentChecksInteractor,
)
from document_scrutiny.interactors.thread_revision import ThreadRevision
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class UpdateDocumentFieldInteractor:
    def __init__(
        self,
        thread_storage: ScrutinyThreadStorageInterface,
        catalog_service: CatalogServiceInterface,
        scrutiny_today: str,
    ):
        self.thread_storage = thread_storage
        self.catalog_service = catalog_service
        self.scrutiny_today = scrutiny_today
        self.revision = ThreadRevision(thread_storage=thread_storage)

    def update_field(
        self, request: UpdateDocumentFieldRequestDTO
    ) -> DocumentChangeDTO:
        thread = self.thread_storage.get_thread(thread_id=request.thread_id)
        document = self.thread_storage.get_document(
            lookup=DocumentLookupDTO(
                thread_id=request.thread_id, document_id=request.document_id
            )
        )
        OfficerActionGuard.check_document_is_not_being_read(document)
        edited = self._apply_edit(document=document, request=request)
        checks, changed_check_ids = self._recheck(
            document=edited, application_id=thread.application_id
        )
        saved, summary = self.revision.save_document(
            thread_id=request.thread_id,
            document=DocumentProgress.with_stage(
                document=edited, stage=edited.stage, checks=checks
            ),
        )
        return DocumentChangeDTO(
            document=saved, summary=summary, changed_check_ids=changed_check_ids
        )

    @staticmethod
    def _apply_edit(
        document: DocumentStateDTO, request: UpdateDocumentFieldRequestDTO
    ) -> DocumentStateDTO:
        if not any(value.key == request.field_key for value in document.field_values):
            raise DocumentFieldNotFound(
                document_id=request.document_id, field_key=request.field_key
            )
        return dataclasses.replace(
            document,
            field_values=tuple(
                dataclasses.replace(
                    value, value=request.value, edited=True, confirmed=False
                )
                if value.key == request.field_key
                else value
                for value in document.field_values
            ),
            # The chain traces the structured record, not the flat values, so a
            # corrected deed field has to reach the record or it re-traces as the
            # misread one. A non-deed field leaves the record untouched.
            deed_record=DeedRecordEdit.apply(
                deed_record=document.deed_record,
                field_key=request.field_key,
                value=request.value,
            ),
            # An edit unsettles the officer's earlier sign-off on this document.
            confirmed=False,
        )

    def _recheck(
        self, document: DocumentStateDTO, application_id: str
    ) -> Tuple[Tuple[CheckDTO, ...], Tuple[str, ...]]:
        recomputed = RunDocumentChecksInteractor().run_checks(
            request=RunDocumentChecksRequestDTO(
                document_id=document.document_id,
                document_type=self.catalog_service.get_document_type(
                    document_type_id=document.document_type_id
                ),
                application=self.catalog_service.get_application(
                    application_id=application_id
                ),
                scrutiny_today=self.scrutiny_today,
                field_values=document.field_values,
                structure_findings=document.structure_findings,
            )
        )
        return CheckReconciliation.merge(
            previous_checks=document.checks, recomputed_checks=tuple(recomputed)
        )
