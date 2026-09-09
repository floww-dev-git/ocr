from typing import Sequence

from document_extraction.dtos.extraction_dtos import DocumentSegmentDTO
from document_scrutiny.constants.bundle_constants import (
    BUNDLE_CHECK_KEY,
    BUNDLE_CLOSING_SENTENCE,
    BUNDLE_TITLE,
    SINGLE_PAGE_RANGE,
)
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.dtos.check_dtos import CheckDTO

FIRST_PAGE_NUMBER = 1


class BundleCheck:
    """What was found inside a bundled file, recorded against the file itself.

    Information, not a finding: nothing is wrong with a file that holds several
    documents, and the officer still needs to be told that the one row they
    attached became four. Each document found is then scrutinised on its own.
    """

    @classmethod
    def build(
        cls, document_id: str, segments: Sequence[DocumentSegmentDTO]
    ) -> CheckDTO:
        return CheckDTO(
            check_id=f"{document_id}:{BUNDLE_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=BUNDLE_TITLE.format(count=len(segments)),
            status=CheckStatus.INFO.value,
            detail=cls._detail(segments=segments),
        )

    @classmethod
    def _detail(cls, segments: Sequence[DocumentSegmentDTO]) -> str:
        found = " ".join(
            f"{cls.describe_pages(segment)}: {segment.document_type_label}."
            for segment in segments
        )
        return f"{found} {BUNDLE_CLOSING_SENTENCE}"

    @staticmethod
    def describe_pages(segment: DocumentSegmentDTO) -> str:
        """Pages as the officer counts them, from one rather than from zero."""
        first = segment.page_start + FIRST_PAGE_NUMBER
        last = segment.page_end + FIRST_PAGE_NUMBER
        if first == last:
            return SINGLE_PAGE_RANGE.format(page=first)
        return f"Pages {first}-{last}"
