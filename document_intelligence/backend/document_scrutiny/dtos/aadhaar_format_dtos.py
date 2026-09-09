from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AadhaarFormatDTO:
    state: str
    rejection_reason: Optional[str] = None
