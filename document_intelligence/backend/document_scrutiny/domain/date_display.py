import re

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def format_iso_date(value: str) -> str:
    if _ISO_DATE.match(str(value or "")) is None:
        return str(value or "")
    year, month, day = value.split("-")
    return f"{day}-{month}-{year}"
