from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class IssuerCallDTO:
    issuer_service_id: str
    name: str
    endpoint: str
    latency_ms: int
    request_payload: Mapping[str, Any]
    response_payload: Optional[Mapping[str, Any]]


@dataclass(frozen=True)
class CheckDTO:
    check_id: str
    document_id: str
    group: str
    title: str
    status: str
    detail: str
    field_key: Optional[str] = None
    acknowledged: bool = False
    manual: bool = False
    requested: bool = False
    issuer_call: Optional[IssuerCallDTO] = None
