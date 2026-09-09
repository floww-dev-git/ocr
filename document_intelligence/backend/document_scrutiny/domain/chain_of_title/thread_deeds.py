from typing import List, Sequence

from document_scrutiny.dtos.chain_dtos import ChainDeedDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO

NO_CONFIDENCE = 0.0


class ThreadDeeds:
    """The registered deeds attached to one thread, in the form the chain reads.

    A document that was never read into a deed record has no transfer to contribute:
    an identity card, a bundle that was segmented rather than read, anything still
    mid-run. None of them is a missing link.
    """

    @classmethod
    def collect(
        cls, documents: Sequence[DocumentStateDTO]
    ) -> List[ChainDeedDTO]:
        return [
            ChainDeedDTO(
                document_id=document.document_id,
                filename=document.filename,
                deed_record=document.deed_record,
                page_start=document.page_start,
                page_end=document.page_end,
                read_confidence=cls._read_confidence(document=document),
            )
            for document in documents
            if document.deed_record is not None
        ]

    @staticmethod
    def _read_confidence(document: DocumentStateDTO) -> float:
        """How well this document was read, averaged over the values read from it.

        Used only to choose between two copies of one registration number, so an
        average is enough: the question is which copy is the better scan.
        """
        confidences = [field_value.confidence for field_value in document.field_values]
        if not confidences:
            return NO_CONFIDENCE
        return sum(confidences) / len(confidences)
