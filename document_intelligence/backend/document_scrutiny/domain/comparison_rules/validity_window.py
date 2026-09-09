from datetime import date, datetime
from typing import Optional

from document_scrutiny.constants.validity_constants import (
    EXPIRING_SOON_DAYS,
    ValidityState,
)
from document_scrutiny.dtos.validity_dtos import ValidityWindowDTO

ISO_DATE_FORMAT = "%Y-%m-%d"


class ValidityWindow:
    """How long a document has left to run, measured against the scrutiny date.

    The date is passed in rather than read from the clock, so a check run is
    reproducible and a demo's seeded expiry dates keep meaning what they were
    written to mean.
    """

    @classmethod
    def inspect(
        cls, valid_until: Optional[str], scrutiny_today: Optional[str]
    ) -> ValidityWindowDTO:
        expiry = cls._parse(valid_until)
        today = cls._parse(scrutiny_today)
        if expiry is None or today is None:
            # Saying nothing is better than saying "valid" about a date nobody read.
            return ValidityWindowDTO(state=ValidityState.UNREADABLE.value)

        days_remaining = (expiry - today).days
        return ValidityWindowDTO(
            state=cls._state(days_remaining), days_remaining=days_remaining
        )

    @staticmethod
    def _state(days_remaining: int) -> str:
        if days_remaining < 0:
            return ValidityState.LAPSED.value
        if days_remaining <= EXPIRING_SOON_DAYS:
            return ValidityState.EXPIRING_SOON.value
        return ValidityState.VALID.value

    @staticmethod
    def _parse(value: Optional[str]) -> Optional[date]:
        candidate = str(value or "").strip()
        if not candidate:
            return None
        try:
            return datetime.strptime(candidate, ISO_DATE_FORMAT).date()
        except ValueError:
            return None
