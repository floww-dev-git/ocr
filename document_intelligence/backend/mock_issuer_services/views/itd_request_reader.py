import re
from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.http import HttpRequest

from mock_issuer_services.constants.itd_constants import DemoOutcome, ItdRequestError
from mock_issuer_services.views.issuer_request_reader import (
    IssuerRequestReader,
    IssuerRequestRejected,
    RequestErrorCodes,
)

_PAN_PATTERN = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")

ITD_ERROR_CODES = RequestErrorCodes(
    api_key_required=ItdRequestError.API_KEY_REQUIRED.value,
    api_key_invalid=ItdRequestError.API_KEY_INVALID.value,
    invalid_request_body=ItdRequestError.INVALID_REQUEST_BODY.value,
    name_required=ItdRequestError.NAME_REQUIRED.value,
    unknown_demo_outcome=ItdRequestError.UNKNOWN_DEMO_OUTCOME.value,
    demo_outcome_not_permitted=ItdRequestError.DEMO_OUTCOME_NOT_PERMITTED.value,
)


@dataclass(frozen=True)
class ItdVerifyRequestDTO:
    pan: str
    name: str
    date_of_birth: Optional[str]
    demo_outcome: DemoOutcome


class ItdRequestReader:
    @classmethod
    def read(cls, request: HttpRequest) -> ItdVerifyRequestDTO:
        IssuerRequestReader.check_api_key(request=request, codes=ITD_ERROR_CODES)
        demo_outcome = IssuerRequestReader.read_demo_outcome(
            request=request, codes=ITD_ERROR_CODES
        )
        payload = IssuerRequestReader.read_payload(
            request=request, codes=ITD_ERROR_CODES
        )
        return ItdVerifyRequestDTO(
            pan=cls._read_pan(payload),
            name=IssuerRequestReader.read_name(
                payload=payload, codes=ITD_ERROR_CODES
            ),
            date_of_birth=IssuerRequestReader.read_text(payload, "dob") or None,
            demo_outcome=demo_outcome,
        )

    @staticmethod
    def _read_pan(payload: Dict[str, Any]) -> str:
        pan = IssuerRequestReader.read_text(payload, "pan")
        if not pan:
            raise IssuerRequestRejected(
                error_code=ItdRequestError.PAN_REQUIRED.value
            )
        pan = pan.upper()
        if _PAN_PATTERN.fullmatch(pan) is None:
            raise IssuerRequestRejected(
                error_code=ItdRequestError.PAN_MALFORMED.value
            )
        return pan
