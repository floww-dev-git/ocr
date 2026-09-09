from document_scrutiny.constants.enums import DocumentStage
from document_scrutiny.domain.abandoned_run_check import AbandonedRunCheck
from document_scrutiny.domain.document_progress import DocumentProgress
from document_scrutiny.domain.officer_action_guard import MID_RUN_STAGES
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.thread_dtos import DocumentLookupDTO, UpdateDocumentDTO
from document_scrutiny.exceptions.scrutiny_exceptions import (
    DocumentNotFound,
    ScrutinyThreadNotFound,
)
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class DocumentRunRecord:
    """Writes down where a run has got to, and closes the record if it stops.

    Separated from the reading pipeline because the two change for different
    reasons: one knows the order documents are read in, the other knows what a
    half-written record must look like so the thread can still settle.
    """

    def __init__(self, thread_storage: ScrutinyThreadStorageInterface):
        self.thread_storage = thread_storage

    def save(self, thread_id: str, document: DocumentStateDTO) -> DocumentStateDTO:
        return self.thread_storage.update_document(
            update_document=UpdateDocumentDTO(thread_id=thread_id, document=document)
        )

    def settle_if_abandoned(self, thread_id: str, document_id: str) -> None:
        document = self._read_or_none(thread_id=thread_id, document_id=document_id)
        if document is None or document.stage not in MID_RUN_STAGES:
            return
        # Recorded as finished so the thread can settle, but carrying the reason,
        # rather than presenting a partial read as a completed one.
        self.save(
            thread_id=thread_id,
            document=DocumentProgress.with_stage(
                document=document,
                stage=DocumentStage.DONE.value,
                checks=document.checks
                + (AbandonedRunCheck.build(document_id=document.document_id),),
            ),
        )

    def _read_or_none(self, thread_id: str, document_id: str):
        try:
            return self.thread_storage.get_document(
                lookup=DocumentLookupDTO(
                    thread_id=thread_id, document_id=document_id
                )
            )
        except (ScrutinyThreadNotFound, DocumentNotFound):
            # The thread was dropped while the run was in flight; there is no
            # record left to close.
            return None
