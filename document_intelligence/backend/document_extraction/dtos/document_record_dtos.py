from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from document_extraction.dtos.deed_record_dtos import DeedRecordDTO


@dataclass(frozen=True)
class FieldBoxDTO:
    field_key: str
    value: str
    page: int
    box: Tuple[int, int, int, int]


@dataclass(frozen=True)
class FieldReadDTO:
    key: str
    value: str
    confidence: float


@dataclass(frozen=True)
class DocumentRecordDTO:
    """One document read into the catalog's own field keys.

    Type-neutral on purpose: every document type reports what it holds as the
    same `key` / `value` / `confidence` triples, so the check engine never has to
    know which kind of paper produced them.
    """

    field_reads: Tuple[FieldReadDTO, ...] = ()
    structure_findings: Mapping[str, bool] = field(default_factory=dict)
    overall_confidence: float = 0.0
    low_confidence_fields: Tuple[str, ...] = ()
    boxes: Tuple[FieldBoxDTO, ...] = ()
    page_count: int = 1
    # Only a registered property document carries one. Everything downstream that
    # reasons about title reads this rather than the flattened field values.
    deed_record: Optional[DeedRecordDTO] = None
    # What a QR printed on the document carries, keyed by the catalog's own field
    # keys (name, aadhaarNo, dob, gender). None when the document has no QR this
    # build could read. The integrity check compares this against the printed reads.
    qr_fields: Optional[Mapping[str, str]] = None
    # A 0..1 legibility score for the scan, with the signals behind it. None when
    # quality was not assessed. The quality check turns a low score into a warning.
    quality: Optional["DocumentQualityDTO"] = None


@dataclass(frozen=True)
class DocumentQualityDTO:
    score: float
    blur_score: float
    resolution_px: int
    legible: bool
