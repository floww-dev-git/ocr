from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LicenceFormatDTO:
    state: str
    state_code: Optional[str] = None
    issue_year: Optional[str] = None
    rejection_reason: Optional[str] = None
