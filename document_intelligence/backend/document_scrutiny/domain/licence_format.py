import re
from typing import Optional

from document_scrutiny.constants.licence_format_constants import (
    EARLIEST_ISSUE_YEAR,
    LATEST_ISSUE_YEAR,
    LICENCE_LENGTHS,
    LONGEST_LICENCE_LENGTH,
    SHORTEST_LICENCE_LENGTH,
    STATE_CODE_LENGTH,
    YEAR_END_FROM_END,
    YEAR_START_FROM_END,
    LicenceFormatState,
)
from document_scrutiny.dtos.licence_format_dtos import LicenceFormatDTO

BLANK_LICENCE_REASON = "No licence number was read from the document."
PATTERN_REASON = (
    "A licence number reads as a two-letter state code followed by thirteen or "
    "fourteen digits, as in TS0920150012345."
)

_LICENCE_PATTERN = re.compile(
    rf"[A-Z]{{{STATE_CODE_LENGTH}}}"
    rf"[0-9]{{{SHORTEST_LICENCE_LENGTH - STATE_CODE_LENGTH},"
    rf"{LONGEST_LICENCE_LENGTH - STATE_CODE_LENGTH}}}"
)


class LicenceFormat:
    """Whether a read value could be an Indian driving licence number.

    Structure only. Which state codes and RTO numbers actually exist is registry
    data this build does not hold, so a well-formed number from an unknown office
    is reported as readable rather than guessed at.
    """

    @classmethod
    def inspect(cls, licence_number: Optional[str]) -> LicenceFormatDTO:
        # A licence is printed with spaces or hyphens as often as without.
        candidate = re.sub(r"[\s-]", "", str(licence_number or "")).upper()
        if not candidate:
            return cls._build_rejection(reason=BLANK_LICENCE_REASON)
        if len(candidate) not in LICENCE_LENGTHS:
            return cls._build_rejection(reason=cls._wrong_length_reason(candidate))
        if _LICENCE_PATTERN.fullmatch(candidate) is None:
            return cls._build_rejection(reason=PATTERN_REASON)

        issue_year = candidate[YEAR_START_FROM_END:YEAR_END_FROM_END]
        state_code = candidate[:STATE_CODE_LENGTH]
        if not cls._year_is_plausible(issue_year):
            return LicenceFormatDTO(
                state=LicenceFormatState.IMPLAUSIBLE_YEAR.value,
                state_code=state_code,
                issue_year=issue_year,
            )
        return LicenceFormatDTO(
            state=LicenceFormatState.RECOGNISED.value,
            state_code=state_code,
            issue_year=issue_year,
        )

    @staticmethod
    def _year_is_plausible(issue_year: str) -> bool:
        return EARLIEST_ISSUE_YEAR <= int(issue_year) <= LATEST_ISSUE_YEAR

    @staticmethod
    def _wrong_length_reason(candidate: str) -> str:
        return (
            f"A licence number is {SHORTEST_LICENCE_LENGTH} or "
            f"{LONGEST_LICENCE_LENGTH} characters; this one reads {len(candidate)}."
        )

    @staticmethod
    def _build_rejection(reason: str) -> LicenceFormatDTO:
        return LicenceFormatDTO(
            state=LicenceFormatState.MALFORMED.value, rejection_reason=reason
        )
