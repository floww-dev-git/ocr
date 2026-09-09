from typing import Dict, List, Sequence, Tuple

from document_extraction.constants.extraction_constants import (
    INVENTORY_FALLBACK_TYPE_ID,
    INVENTORY_TYPE_KEYWORDS,
    NON_TITLE_WORD,
    PRIOR_TITLE_TYPE_ID,
    TITLE_DEED_KINDS,
    TITLE_DEED_TYPE_IDS,
)
from document_extraction.dtos.inventory_dtos import PageBoundaryDTO, PageSegmentDTO

FIRST_PAGE = 0


class PageSegments:
    """Turns per-page boundary signals into the documents a file actually holds.

    Grouping is carried from sale_deed_poc/build/poc/extract.py: page 0 always
    starts a document, and a document runs until the page before the next start.
    Over-segmenting is the safer error, because two deeds merged into one read
    report a single chain link where there were two.
    """

    @classmethod
    def group(
        cls, boundaries: Sequence[PageBoundaryDTO], page_count: int
    ) -> Tuple[PageSegmentDTO, ...]:
        if page_count <= 0:
            return ()
        starts = cls._read_starts(boundaries=boundaries, page_count=page_count)
        segments = [
            cls._build_segment(
                start=start,
                page_end=cls._page_end(
                    starts=starts, index=index, page_count=page_count
                ),
            )
            for index, start in enumerate(starts)
        ]
        return cls._assign_title_roles(segments=segments)

    @staticmethod
    def single(page_count: int, document_type_id: str) -> Tuple[PageSegmentDTO, ...]:
        """The file holds one document. Stated as a segment so callers need no branch."""
        return (
            PageSegmentDTO(
                page_start=FIRST_PAGE,
                page_end=max(FIRST_PAGE, page_count - 1),
                document_type_id=document_type_id,
                is_title_doc=document_type_id in TITLE_DEED_TYPE_IDS,
            ),
        )

    @staticmethod
    def is_title_doc(doc_type: str) -> bool:
        lowered = str(doc_type or "").lower()
        return (
            any(kind in lowered for kind in TITLE_DEED_KINDS)
            and NON_TITLE_WORD not in lowered
        )

    @staticmethod
    def resolve_document_type_id(doc_type: str) -> str:
        lowered = str(doc_type or "").lower()
        for keyword, document_type_id in INVENTORY_TYPE_KEYWORDS:
            if keyword in lowered:
                return document_type_id
        if PageSegments.is_title_doc(doc_type):
            return PRIOR_TITLE_TYPE_ID
        return INVENTORY_FALLBACK_TYPE_ID

    @staticmethod
    def _read_starts(
        boundaries: Sequence[PageBoundaryDTO], page_count: int
    ) -> List[PageBoundaryDTO]:
        by_page: Dict[int, PageBoundaryDTO] = {
            boundary.page: boundary
            for boundary in boundaries
            if FIRST_PAGE <= boundary.page < page_count
        }
        starts: List[PageBoundaryDTO] = []
        for page in range(page_count):
            boundary = by_page.get(page)
            # The first content page always starts a document, whatever the model
            # said, so a file can never come back with no documents in it.
            if page == FIRST_PAGE:
                starts.append(
                    boundary or PageBoundaryDTO(page=page, starts_new_document=True)
                )
            elif boundary is not None and boundary.starts_new_document:
                starts.append(boundary)
        return starts

    @staticmethod
    def _page_end(
        starts: Sequence[PageBoundaryDTO], index: int, page_count: int
    ) -> int:
        if index + 1 < len(starts):
            return starts[index + 1].page - 1
        return page_count - 1

    @classmethod
    def _build_segment(
        cls, start: PageBoundaryDTO, page_end: int
    ) -> PageSegmentDTO:
        doc_type = start.doc_type or ""
        return PageSegmentDTO(
            page_start=start.page,
            page_end=max(start.page, page_end),
            document_type_id=cls.resolve_document_type_id(doc_type),
            summary=start.summary,
            is_title_doc=cls.is_title_doc(doc_type),
        )

    @staticmethod
    def _assign_title_roles(
        segments: Sequence[PageSegmentDTO],
    ) -> Tuple[PageSegmentDTO, ...]:
        """Only the last title deed in the file is the one being relied on.

        A bundle is a current deed photocopied together with the deeds behind it,
        so every title deed but the last is a link document. Without this the
        officer is asked why a 2003 vendor is not the 2026 applicant.
        """
        title_indexes = [
            index for index, segment in enumerate(segments) if segment.is_title_doc
        ]
        if len(title_indexes) < 2:
            return tuple(segments)
        current_index = title_indexes[-1]
        return tuple(
            segment
            if index == current_index or not segment.is_title_doc
            else PageSegmentDTO(
                page_start=segment.page_start,
                page_end=segment.page_end,
                document_type_id=PRIOR_TITLE_TYPE_ID,
                summary=segment.summary,
                is_title_doc=segment.is_title_doc,
            )
            for index, segment in enumerate(segments)
        )
