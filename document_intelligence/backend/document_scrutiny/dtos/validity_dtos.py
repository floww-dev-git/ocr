from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ValidityWindowDTO:
    state: str
    # Negative once the date has passed. None when either date could not be read.
    days_remaining: Optional[int] = None
