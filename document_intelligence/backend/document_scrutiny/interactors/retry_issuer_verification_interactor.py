import dataclasses
from typing import Optional

from document_catalog.app_interfaces.catalog_service_interface import (
    CatalogServiceInterface,
)
from document_catalog.dtos.catalog_dtos import DocumentTypeDTO
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.officer_action_guard import OfficerActionGuard
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.officer_action_dtos import (
    CheckChangeDTO,
    RetryIssuerVerificationRequestDTO,
)
from document_scrutiny.dtos.thread_dtos import DocumentLookupDTO
from document_scrutiny.exceptions.scrutiny_exceptions import (
    CheckNotRetryable,
    IssuerCheckMissing,
    NoIssuerToRetry,
)
from document_scrutiny.interactors.issuer_consultation import IssuerConsultation
from document_scrutiny.interactors.thread_revision import ThreadRevision
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class RetryIssuerVerificationInteractor:
    def __init__(
        self,
        thread_storage: ScrutinyThreadStorageInterface,
        catalog_service: CatalogServiceInterface,
        consultation: IssuerConsultation,
    ):
        self.thread_storage = thread_storage
        self.catalog_service = catalog_service
        self.consultation = consultation
        self.revision = ThreadRevision(thread_storage=thread_storage)

    def retry_verification(
        self, request: RetryIssuerVerificationRequestDTO
    ) -> CheckChangeDTO:
        thread = self.thread_storage.get_thread(thread_id=request.thread_id)
        document = self.thread_storage.get_document(
            lookup=DocumentLookupDTO(
                thread_id=request.thread_id, document_id=request.document_id
            )
        )
        OfficerActionGuard.check_document_is_not_being_read(document)
        document_type = self.catalog_service.get_document_type(
            document_type_id=document.document_type_id
        )
        self._validate_issuer_can_be_asked_again(
            document=document, document_type=document_type
        )
        fresh = self.consultation.consult(
            thread=thread, document=document, document_type=document_type
        )
        saved, summary = self.revision.save_document(
            thread_id=request.thread_id,
            document=self._replace_issuer_check(document=document, fresh=fresh),
        )
        return CheckChangeDTO(check=fresh, document=saved, summary=summary)

    @staticmethod
    def _validate_issuer_can_be_asked_again(
        document: DocumentStateDTO, document_type: DocumentTypeDTO
    ) -> None:
        if document_type.issuer_service_id is None:
            # Nothing was asked in the first place: this type's department publishes
            # no interface. Re-asking would run the same non-call and report it as a
            # fresh attempt, which is worse than saying so plainly. Asked of the
            # catalog rather than of the check, because whether a department can be
            # reached at all is a fact about the type, not about one answer.
            raise NoIssuerToRetry(document_id=document.document_id)
        existing: Optional[CheckDTO] = next(
            (
                check
                for check in document.checks
                if check.group == CheckGroup.EXTERNAL.value
            ),
            None,
        )
        if existing is None:
            raise IssuerCheckMissing(document_id=document.document_id)
        if existing.status == CheckStatus.PASS.value:
            # Re-asking a department that already agreed spends a call and invites
            # a different answer to a settled question.
            raise CheckNotRetryable(
                check_id=existing.check_id, status=existing.status
            )

    @staticmethod
    def _replace_issuer_check(
        document: DocumentStateDTO, fresh: CheckDTO
    ) -> DocumentStateDTO:
        # A fresh answer arrives unresolved: any earlier acknowledgement was
        # about the answer it replaces.
        return dataclasses.replace(
            document,
            checks=tuple(
                fresh if check.check_id == fresh.check_id else check
                for check in document.checks
            ),
        )
