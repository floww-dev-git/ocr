import dataclasses

from document_scrutiny.dtos.officer_action_dtos import (
    ConfirmDocumentFieldsRequestDTO,
    DocumentChangeDTO,
)
from document_scrutiny.domain.officer_action_guard import OfficerActionGuard
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.thread_dtos import DocumentLookupDTO
from document_scrutiny.exceptions.scrutiny_exceptions import NothingToConfirm
from document_scrutiny.interactors.thread_revision import ThreadRevision
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class ConfirmDocumentFieldsInteractor:
    def __init__(self, thread_storage: ScrutinyThreadStorageInterface):
        self.thread_storage = thread_storage
        self.revision = ThreadRevision(thread_storage=thread_storage)

    def confirm_fields(
        self, request: ConfirmDocumentFieldsRequestDTO
    ) -> DocumentChangeDTO:
        document = self.thread_storage.get_document(
            lookup=DocumentLookupDTO(
                thread_id=request.thread_id, document_id=request.document_id
            )
        )
        OfficerActionGuard.check_document_is_not_being_read(document)
        self._check_there_is_something_to_vouch_for(document)
        saved, summary = self.revision.save_document(
            thread_id=request.thread_id,
            document=dataclasses.replace(
                document,
                field_values=tuple(
                    dataclasses.replace(value, confirmed=True)
                    for value in document.field_values
                ),
                confirmed=True,
            ),
        )
        return DocumentChangeDTO(document=saved, summary=summary)

    @staticmethod
    def _check_there_is_something_to_vouch_for(document: DocumentStateDTO) -> None:
        # Sign-off means "I have read these values and they are right". Over an
        # empty field set that is an assertion about nothing, and it still counts
        # towards the confirmed tally a reviewer reads.
        if not document.field_values:
            raise NothingToConfirm(document_id=document.document_id)
