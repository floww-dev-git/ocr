from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PageBoundaryDTO:
    """One page's answer to "does a new registered document begin here?".

    The model's own reading of a single page, before any grouping. Kept separate
    from the schema it arrives in so the grouping logic never sees pydantic.
    """

    page: int
    starts_new_document: bool
    doc_type: Optional[str] = None
    doc_no: Optional[str] = None
    summary: Optional[str] = None


@dataclass(frozen=True)
class PageSegmentDTO:
    """One document located inside an uploaded file, before the catalog is consulted.

    `document_type_id` is the catalog id the inventory's free-text `doc_type` was
    resolved to; the label, confidence and support flag are added by the adapter,
    which is the only layer that may talk to the catalog.
    """

    page_start: int
    page_end: int
    document_type_id: str
    summary: Optional[str] = None
    is_title_doc: bool = True
