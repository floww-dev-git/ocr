from typing import Dict, List, Sequence, Tuple

from document_scrutiny.constants.enums import CheckStatus, DocumentStage, ThreadStatus
from document_scrutiny.domain.open_check import is_open
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.summary_dtos import OpenItemDTO, ScrutinySummaryDTO


class ScrutinySummary:
    @classmethod
    def summarise(cls, documents: Sequence[DocumentStateDTO]) -> ScrutinySummaryDTO:
        open_items = cls._collect_open_items(documents)
        return ScrutinySummaryDTO(
            thread_status=cls._derive_thread_status(
                documents=documents, open_item_count=len(open_items)
            ),
            document_count=len(documents),
            confirmed_document_count=sum(
                1 for document in documents if document.confirmed
            ),
            status_counts=cls._count_statuses(documents),
            open_items=open_items,
        )

    @staticmethod
    def _derive_thread_status(
        documents: Sequence[DocumentStateDTO], open_item_count: int
    ) -> str:
        if not documents:
            return ThreadStatus.NEW.value
        still_reading = any(
            document.stage != DocumentStage.DONE.value for document in documents
        )
        if still_reading:
            return ThreadStatus.RUNNING.value
        if open_item_count:
            return ThreadStatus.ATTENTION.value
        return ThreadStatus.CLEAR.value

    @staticmethod
    def _count_statuses(documents: Sequence[DocumentStateDTO]) -> Dict[str, int]:
        counts = {status.value: 0 for status in CheckStatus}
        for document in documents:
            for check in document.checks:
                # A status outside the vocabulary must not take down the summary,
                # the note and every officer action at once.
                counts[check.status] = counts.get(check.status, 0) + 1
        return counts

    @staticmethod
    def _collect_open_items(
        documents: Sequence[DocumentStateDTO],
    ) -> Tuple[OpenItemDTO, ...]:
        open_items: List[OpenItemDTO] = []
        for document in documents:
            for check in document.checks:
                if not is_open(check):
                    continue
                open_items.append(
                    OpenItemDTO(
                        document_id=document.document_id,
                        check_id=check.check_id,
                        text=f"{document.document_type_label}: {check.title}",
                    )
                )
        return tuple(open_items)
