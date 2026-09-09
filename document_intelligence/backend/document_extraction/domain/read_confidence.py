from typing import Sequence, Tuple

from common.rounding import round_half_up
from document_extraction.constants.extraction_constants import (
    CONFIDENCE_DECIMAL_PLACES,
    LOW_CONFIDENCE_THRESHOLD,
    UPLOAD_CONFIDENCE_FACTOR,
    DocumentSource,
)
from document_extraction.dtos.document_record_dtos import FieldReadDTO


class ReadConfidence:
    @staticmethod
    def for_source(confidence: float, source: str) -> float:
        if source == DocumentSource.UPLOAD.value:
            confidence = confidence * UPLOAD_CONFIDENCE_FACTOR
        return round_half_up(confidence, CONFIDENCE_DECIMAL_PLACES)

    @staticmethod
    def collect_low_confidence_field_keys(
        field_reads: Sequence[FieldReadDTO],
    ) -> Tuple[str, ...]:
        return tuple(
            field_read.key
            for field_read in field_reads
            if field_read.confidence < LOW_CONFIDENCE_THRESHOLD
        )

    @staticmethod
    def overall(field_reads: Sequence[FieldReadDTO]) -> float:
        if not field_reads:
            return 0.0
        return min(field_read.confidence for field_read in field_reads)
