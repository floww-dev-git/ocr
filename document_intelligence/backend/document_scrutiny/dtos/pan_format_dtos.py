from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PanFormatDTO:
    state: str
    holder_type_code: Optional[str]
    holder_type_label: Optional[str]
    rejection_reason: Optional[str]
