from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple


@dataclass(frozen=True)
class IssuerAnswerFactsDTO:
    outcome: str
    latency_ms: int
    request_payload: Mapping[str, Any] = field(default_factory=dict)
    response_payload: Optional[Mapping[str, Any]] = None
    disagreeing_fields: Tuple[str, ...] = ()
    unreachable_reason: Optional[str] = None
