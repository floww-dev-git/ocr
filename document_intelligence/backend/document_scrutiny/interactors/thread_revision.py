from typing import Tuple

from document_scrutiny.domain.document_progress import DocumentProgress
from document_scrutiny.domain.scrutiny_summary import ScrutinySummary
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.summary_dtos import ScrutinySummaryDTO
from document_scrutiny.dtos.thread_dtos import UpdateDocumentDTO
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class ThreadRevision:
    """Persists one document and re-reads the thread it belongs to, so the
    officer always gets the whole-thread consequence of a single edit."""

    def __init__(self, thread_storage: ScrutinyThreadStorageInterface):
        self.thread_storage = thread_storage

    def save_document(
        self, thread_id: str, document: DocumentStateDTO
    ) -> Tuple[DocumentStateDTO, ScrutinySummaryDTO]:
        saved = self.thread_storage.update_document(
            update_document=UpdateDocumentDTO(
                thread_id=thread_id,
                # Resolving or replacing a check changes what the document as a
                # whole amounts to, so its verdict is re-derived here rather than
                # left to each caller to remember.
                document=DocumentProgress.with_stage(
                    document=document, stage=document.stage
                ),
            )
        )
        thread = self.thread_storage.get_thread(thread_id=thread_id)
        return saved, ScrutinySummary.summarise(thread.documents)
