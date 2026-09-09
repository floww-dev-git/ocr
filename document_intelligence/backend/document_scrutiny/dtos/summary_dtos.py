from dataclasses import dataclass
from typing import Mapping, Tuple


@dataclass(frozen=True)
class OpenItemDTO:
    document_id: str
    check_id: str
    text: str


@dataclass(frozen=True)
class ScrutinySummaryDTO:
    thread_status: str
    document_count: int
    confirmed_document_count: int
    status_counts: Mapping[str, int]
    open_items: Tuple[OpenItemDTO, ...]
