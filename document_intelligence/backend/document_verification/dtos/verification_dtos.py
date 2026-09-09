from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Tuple

from document_verification.constants.verification_constants import ServiceOverride


@dataclass(frozen=True)
class VerifyDocumentRequestDTO:
    """One question to put to one issuing department.

    `lookup_values` is everything that was read off the document, keyed by the
    catalog's own field keys. Each adapter picks out and renames what its own
    issuer asks for, because the wire format belongs to the issuer, not here.
    """

    document_id: str
    issuer_service_id: str
    lookup_values: Mapping[str, str] = field(default_factory=dict)
    service_override: str = ServiceOverride.AUTO.value


@dataclass(frozen=True)
class IssuerAnswerDTO:
    outcome: str
    latency_ms: int
    request_payload: Mapping[str, Any] = field(default_factory=dict)
    response_payload: Optional[Mapping[str, Any]] = None
    disagreeing_fields: Tuple[str, ...] = ()
    unreachable_reason: Optional[str] = None
