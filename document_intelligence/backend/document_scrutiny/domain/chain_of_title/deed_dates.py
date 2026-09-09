import re
from datetime import date, datetime
from typing import Optional

from document_scrutiny.constants.chain_constants import DEED_DATE_FORMATS

_YEAR = re.compile(r"(\d{4})")
FIRST_OF_JANUARY = (1, 1)


class DeedDates:
    """Reads the date off a deed, however that deed chose to write it.

    A registered document may be dated in any of half a dozen conventions, and a
    photocopy of a 1987 deed often yields little more than a year. Falling back to the
    year keeps such a deed in the timeline instead of dropping it to the front.
    """

    @classmethod
    def read(cls, value: Optional[str]) -> Optional[date]:
        text = str(value or "").strip()
        if not text:
            return None
        for date_format in DEED_DATE_FORMATS:
            parsed = cls._try_format(text=text, date_format=date_format)
            if parsed is not None:
                return parsed
        return cls._year_only(text)

    @staticmethod
    def _try_format(text: str, date_format: str) -> Optional[date]:
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            return None

    @staticmethod
    def _year_only(text: str) -> Optional[date]:
        found = _YEAR.search(text)
        if found is None:
            return None
        month, day = FIRST_OF_JANUARY
        try:
            return date(int(found.group(1)), month, day)
        except ValueError:
            return None

    @classmethod
    def sort_key(cls, value: Optional[str]) -> date:
        """A deed with no readable date sorts first, so it never displaces a dated one."""
        return cls.read(value) or date.min
