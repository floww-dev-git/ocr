from datetime import date, datetime
from typing import Optional

from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.internal_consistency_constants import (
    INTERNAL_CONSISTENCY_CHECK_KEY,
    MAX_PLAUSIBLE_AGE_YEARS,
    YEAR_ONLY_MONTH_DAY,
)
from document_scrutiny.domain.date_display import format_iso_date
from document_scrutiny.dtos.check_dtos import CheckDTO

_ISO_DATE_FORMAT = "%Y-%m-%d"

PLAUSIBLE_TITLE = "Date of birth is plausible"
PLAUSIBLE_DETAIL = "The date of birth reads as a real, plausible date."
FUTURE_TITLE = "Date of birth is in the future"
FUTURE_DETAIL = (
    "The date of birth read from the document is later than the date of scrutiny, "
    "so the document is not internally consistent. Check the original."
)
TOO_OLD_TITLE = "Date of birth is implausibly old"
TOO_OLD_DETAIL = (
    "The date of birth read from the document implies an age over "
    f"{MAX_PLAUSIBLE_AGE_YEARS}, which no genuine document would carry. Check the "
    "original."
)
UNREADABLE_TITLE = "Date of birth could not be read as a date"
UNREADABLE_DETAIL = (
    "The date of birth is not a readable calendar date, so it could not be checked "
    "for consistency. Verify it against the original."
)
YEAR_ONLY_TITLE = "Date of birth may be year-only"
YEAR_ONLY_DETAIL = (
    "The document appears to carry only a year of birth, recorded as the first of "
    "January. Confirm the full date of birth against the original."
)


class InternalConsistencyCheck:
    """Whether the document's own dates hold together, judged from the document alone.

    An intrinsic check: it compares nothing against the application or a department,
    only against the calendar and the date of scrutiny. A date of birth in the
    future or implying an impossible age is the document contradicting itself, and
    is caught before any cross-check has an opinion. A year-only date (normalised to
    01-01 by the reader) is a soft flag to confirm the full date, not a failure.

    Returns None when there is no date of birth to judge, so a document type that
    carries none is simply not checked here.
    """

    @classmethod
    def build(
        cls,
        document_id: str,
        date_of_birth: Optional[str],
        scrutiny_today: str,
    ) -> Optional[CheckDTO]:
        if not str(date_of_birth or "").strip():
            return None
        parsed = cls._parse(date_of_birth)
        today = cls._parse(scrutiny_today)
        if parsed is None:
            return cls._check(
                document_id=document_id,
                status=CheckStatus.WARN.value,
                title=UNREADABLE_TITLE,
                detail=UNREADABLE_DETAIL,
            )
        if today is not None and parsed > today:
            return cls._check(
                document_id=document_id,
                status=CheckStatus.FAIL.value,
                title=FUTURE_TITLE,
                detail=FUTURE_DETAIL,
            )
        if today is not None and cls._years_between(parsed, today) > MAX_PLAUSIBLE_AGE_YEARS:
            return cls._check(
                document_id=document_id,
                status=CheckStatus.FAIL.value,
                title=TOO_OLD_TITLE,
                detail=TOO_OLD_DETAIL,
            )
        if (parsed.month, parsed.day) == YEAR_ONLY_MONTH_DAY:
            return cls._check(
                document_id=document_id,
                status=CheckStatus.WARN.value,
                title=YEAR_ONLY_TITLE,
                detail=YEAR_ONLY_DETAIL,
            )
        return cls._check(
            document_id=document_id,
            status=CheckStatus.PASS.value,
            title=PLAUSIBLE_TITLE,
            detail=f"{PLAUSIBLE_DETAIL.rstrip('.')}: {format_iso_date(date_of_birth)}.",
        )

    @staticmethod
    def _parse(value: Optional[str]) -> Optional[date]:
        try:
            return datetime.strptime(str(value or "").strip(), _ISO_DATE_FORMAT).date()
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _years_between(earlier: date, later: date) -> int:
        years = later.year - earlier.year
        if (later.month, later.day) < (earlier.month, earlier.day):
            years -= 1
        return years

    @staticmethod
    def _check(
        document_id: str, status: str, title: str, detail: str
    ) -> CheckDTO:
        return CheckDTO(
            check_id=f"{document_id}:{INTERNAL_CONSISTENCY_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=title,
            status=status,
            detail=detail,
        )
