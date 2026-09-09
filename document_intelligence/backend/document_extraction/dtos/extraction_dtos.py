from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ExtractDocumentRequestDTO:
    filename: str
    application_id: str
    source: str
    file_path: Optional[str] = None
    # Set from the classification before extraction, so the reader knows which
    # type's schema and prompt to use. Absent while classifying, because that is
    # the question classification is answering.
    document_type_id: Optional[str] = None
    # Set when the request addresses one document inside a bundled file. A slice is
    # never segmented again: the pass that carved it out already did that work.
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    @property
    def is_page_slice(self) -> bool:
        return self.page_start is not None


@dataclass(frozen=True)
class DocumentSegmentDTO:
    """One document found inside an uploaded file, named in the catalog's terms.

    A file that holds a single document reports one segment spanning all its
    pages, so a caller never has to tell the two cases apart.
    """

    document_type_id: str
    document_type_label: str
    type_confidence: float
    implemented: bool
    page_start: int
    page_end: int
    summary: Optional[str] = None
    is_title_doc: bool = True

    @property
    def page_count(self) -> int:
        return self.page_end - self.page_start + 1


@dataclass(frozen=True)
class DocumentClassificationDTO:
    document_type_id: str
    document_type_label: str
    type_confidence: float
    implemented: bool
    page_count: int
    total_page_count: int
    segments: Tuple[DocumentSegmentDTO, ...] = ()

    @property
    def is_bundle(self) -> bool:
        """More than one registered document was photocopied into this one file."""
        return len(self.segments) > 1
