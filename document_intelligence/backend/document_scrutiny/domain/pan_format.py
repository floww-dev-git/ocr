import re
from typing import Optional

from document_scrutiny.constants.pan_holder_types import (
    DIGIT_BLOCK_LENGTH,
    HOLDER_TYPE_LABELS_BY_CODE,
    HOLDER_TYPE_POSITION,
    LETTER_PREFIX_LENGTH,
    LETTER_SUFFIX_LENGTH,
    PAN_LENGTH,
    PanFormatState,
)
from document_scrutiny.dtos.pan_format_dtos import PanFormatDTO

BLANK_PAN_REASON = "No PAN was read from the document."
PATTERN_REASON = "A PAN reads as five letters, four digits, then a letter."

_PAN_PATTERN = re.compile(
    rf"[A-Z]{{{LETTER_PREFIX_LENGTH}}}[0-9]{{{DIGIT_BLOCK_LENGTH}}}[A-Z]{{{LETTER_SUFFIX_LENGTH}}}"
)


class PanFormat:
    @classmethod
    def inspect(cls, pan: Optional[str]) -> PanFormatDTO:
        candidate = str(pan or "").strip()
        if not candidate:
            return cls._build_rejection(reason=BLANK_PAN_REASON)
        if len(candidate) != PAN_LENGTH:
            return cls._build_rejection(reason=cls._wrong_length_reason(candidate))
        if _PAN_PATTERN.fullmatch(candidate) is None:
            return cls._build_rejection(reason=PATTERN_REASON)

        holder_type_code = candidate[HOLDER_TYPE_POSITION]
        holder_type_label = HOLDER_TYPE_LABELS_BY_CODE.get(holder_type_code)
        return PanFormatDTO(
            state=cls._recognition_state(holder_type_label),
            holder_type_code=holder_type_code,
            holder_type_label=holder_type_label,
            rejection_reason=None,
        )

    @staticmethod
    def _recognition_state(holder_type_label: Optional[str]) -> str:
        if holder_type_label is None:
            return PanFormatState.UNRECOGNISED_HOLDER_TYPE.value
        return PanFormatState.RECOGNISED.value

    @staticmethod
    def _wrong_length_reason(candidate: str) -> str:
        return f"A PAN is {PAN_LENGTH} characters; this one reads {len(candidate)}."

    @staticmethod
    def _build_rejection(reason: str) -> PanFormatDTO:
        return PanFormatDTO(
            state=PanFormatState.MALFORMED.value,
            holder_type_code=None,
            holder_type_label=None,
            rejection_reason=reason,
        )
