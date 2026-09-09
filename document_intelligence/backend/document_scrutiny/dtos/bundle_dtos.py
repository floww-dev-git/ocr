from dataclasses import dataclass
from typing import Tuple

from document_extraction.dtos.extraction_dtos import DocumentSegmentDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO


@dataclass(frozen=True)
class SegmentBundleRequestDTO:
    thread_id: str
    document_id: str
    segments: Tuple[DocumentSegmentDTO, ...]


@dataclass(frozen=True)
class BundleSegmentationDTO:
    """The bundle as it now stands, and the documents that came out of it."""

    parent: DocumentStateDTO
    children: Tuple[DocumentStateDTO, ...]
