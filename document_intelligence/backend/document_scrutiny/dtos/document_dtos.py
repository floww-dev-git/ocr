from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from document_extraction.dtos.deed_record_dtos import DeedRecordDTO
from document_extraction.dtos.document_record_dtos import DocumentQualityDTO
from document_scrutiny.dtos.check_dtos import CheckDTO


@dataclass(frozen=True)
class FieldValueDTO:
    key: str
    value: str
    confidence: float
    edited: bool = False
    confirmed: bool = False


@dataclass(frozen=True)
class DocumentStateDTO:
    document_id: str
    filename: str
    file_format: str
    file_size_bytes: int
    document_type_id: Optional[str]
    document_type_label: str
    type_confidence: float
    implemented: bool
    stage: str
    status: str
    confirmed: bool
    page_count: int
    field_values: Tuple[FieldValueDTO, ...] = ()
    structure_findings: Mapping[str, bool] = field(default_factory=dict)
    checks: Tuple[CheckDTO, ...] = ()
    page_image_urls: Tuple[str, ...] = ()
    # Only a registered property document carries one. The flat field values above
    # are the officer's surface; this is what reasoning about title reads.
    deed_record: Optional[DeedRecordDTO] = None
    # Set on one document carved out of a bundled file. It has no file of its own:
    # it is a page range of its parent's, and it is read from there.
    parent_document_id: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    # What a QR on the document carries (keyed by catalog field key), for the
    # integrity check to compare against the printed reads. None when there is none.
    qr_fields: Optional[Mapping[str, str]] = None
    # How legible the scan was judged to be. None when quality was not assessed.
    quality: Optional[DocumentQualityDTO] = None
