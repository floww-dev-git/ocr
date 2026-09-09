import re
from typing import Optional

_NON_ALPHANUMERIC = re.compile(r"[^A-Z0-9 ]")
_DAY_FIRST_DATE = re.compile(r"(\d{2})[-/](\d{2})[-/](\d{4})")
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def names_agree(submitted_name: str, registered_name: str) -> bool:
    """Whether two spellings of a name are the same name to a registry.

    Shared across departments so that a name accepted by one is accepted by all:
    an officer comparing two cards should not find that one department is fussier
    about a full stop than another.
    """
    return normalise_name(submitted_name) == normalise_name(registered_name)


def normalise_name(name: str) -> str:
    uppercased = _NON_ALPHANUMERIC.sub(" ", str(name).upper())
    return " ".join(uppercased.split())


def words_agree(submitted: str, registered: str) -> bool:
    return normalise_words(submitted) == normalise_words(registered)


def normalise_words(value: str) -> str:
    return " ".join(str(value).lower().split())


def dates_agree(submitted_date: Optional[str], registered_date: str) -> Optional[bool]:
    """None when nothing was submitted: a department answers only what it was asked."""
    if submitted_date is None:
        return None
    return normalise_date(submitted_date) == registered_date


def normalise_date(value: str) -> str:
    candidate = str(value).strip()
    if _ISO_DATE.fullmatch(candidate):
        return candidate
    day_first = _DAY_FIRST_DATE.fullmatch(candidate)
    if day_first is None:
        return candidate
    day, month, year = day_first.groups()
    return f"{year}-{month}-{day}"
