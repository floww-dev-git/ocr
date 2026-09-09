from typing import Optional

from document_scrutiny.constants.aadhaar_format_constants import (
    AADHAAR_LENGTH,
    AADHAAR_LENGTH_IN_WORDS,
    CHECKSUM_FAILED_REASON,
    DISALLOWED_LEADING_DIGITS,
    AadhaarFormatState,
)
from document_scrutiny.domain.aadhaar_verhoeff import is_verhoeff_valid
from document_scrutiny.dtos.aadhaar_format_dtos import AadhaarFormatDTO

BLANK_AADHAAR_REASON = "No Aadhaar number was read from the document."
NON_DIGIT_REASON = "An Aadhaar number is twelve digits and nothing else."
LEADING_DIGIT_REASON = (
    "An Aadhaar number does not begin with 0 or 1. This one does, so it is "
    "some other twelve-digit number."
)


class AadhaarFormat:
    """Whether a read value could be an Aadhaar number.

    Structure always; the Verhoeff check digit only when `verify_checksum` is asked
    for. It is off by default because the legacy seeded applications carry invented
    numbers that would all fail it (ADR-009); the Aadhaar showcase, which uses
    generated specimens whose numbers are checksum-valid on purpose, turns it on so
    the checksum is a real, honest capability there. A checksum switched off for the
    data it is meant to guard is worse than none — so it is enabled exactly where
    the data was built to satisfy it (ADR-013).
    """

    @classmethod
    def inspect(
        cls, aadhaar_number: Optional[str], verify_checksum: bool = False
    ) -> AadhaarFormatDTO:
        digits = "".join(str(aadhaar_number or "").split())
        if not digits:
            return cls._build_rejection(reason=BLANK_AADHAAR_REASON)
        if not digits.isdigit():
            return cls._build_rejection(reason=NON_DIGIT_REASON)
        if len(digits) != AADHAAR_LENGTH:
            return cls._build_rejection(reason=cls._wrong_length_reason(digits))
        if digits[0] in DISALLOWED_LEADING_DIGITS:
            return cls._build_rejection(reason=LEADING_DIGIT_REASON)
        if verify_checksum and not is_verhoeff_valid(digits):
            return AadhaarFormatDTO(
                state=AadhaarFormatState.CHECKSUM_FAILED.value,
                rejection_reason=CHECKSUM_FAILED_REASON,
            )
        return AadhaarFormatDTO(state=AadhaarFormatState.RECOGNISED.value)

    @staticmethod
    def _wrong_length_reason(digits: str) -> str:
        return (
            f"An Aadhaar number is {AADHAAR_LENGTH_IN_WORDS} digits; "
            f"this one reads {len(digits)}."
        )

    @staticmethod
    def _build_rejection(reason: str) -> AadhaarFormatDTO:
        return AadhaarFormatDTO(
            state=AadhaarFormatState.MALFORMED.value, rejection_reason=reason
        )
