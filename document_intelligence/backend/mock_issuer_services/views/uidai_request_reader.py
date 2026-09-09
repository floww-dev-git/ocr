from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.http import HttpRequest

from mock_issuer_services.constants.issuer_http_constants import DemoOutcome
from mock_issuer_services.constants.uidai_constants import UidaiRequestError
from mock_issuer_services.views.issuer_request_reader import (
    IssuerRequestReader,
    IssuerRequestRejected,
    RequestErrorCodes,
)

AADHAAR_LENGTH = 12
DISALLOWED_LEADING_DIGITS = ("0", "1")

UIDAI_ERROR_CODES = RequestErrorCodes(
    api_key_required=UidaiRequestError.API_KEY_REQUIRED.value,
    api_key_invalid=UidaiRequestError.API_KEY_INVALID.value,
    invalid_request_body=UidaiRequestError.INVALID_REQUEST_BODY.value,
    name_required=UidaiRequestError.NAME_REQUIRED.value,
    unknown_demo_outcome=UidaiRequestError.UNKNOWN_DEMO_OUTCOME.value,
    demo_outcome_not_permitted=UidaiRequestError.DEMO_OUTCOME_NOT_PERMITTED.value,
)


@dataclass(frozen=True)
class UidaiVerifyRequestDTO:
    aadhaar_number: str
    name: str
    date_of_birth: Optional[str]
    gender: Optional[str]
    demo_outcome: DemoOutcome


class UidaiRequestReader:
    @classmethod
    def read(cls, request: HttpRequest) -> UidaiVerifyRequestDTO:
        IssuerRequestReader.check_api_key(request=request, codes=UIDAI_ERROR_CODES)
        demo_outcome = IssuerRequestReader.read_demo_outcome(
            request=request, codes=UIDAI_ERROR_CODES
        )
        payload = IssuerRequestReader.read_payload(
            request=request, codes=UIDAI_ERROR_CODES
        )
        return UidaiVerifyRequestDTO(
            aadhaar_number=cls._read_aadhaar_number(payload),
            name=IssuerRequestReader.read_name(
                payload=payload, codes=UIDAI_ERROR_CODES
            ),
            date_of_birth=IssuerRequestReader.read_text(payload, "dob") or None,
            gender=IssuerRequestReader.read_text(payload, "gender") or None,
            demo_outcome=demo_outcome,
        )

    @staticmethod
    def _read_aadhaar_number(payload: Dict[str, Any]) -> str:
        # Spaces are accepted because the number is printed in groups of four and a
        # caller may well submit it that way; anything else is refused.
        submitted = IssuerRequestReader.read_text(payload, "aadhaarNo")
        digits = "".join(submitted.split())
        if not digits:
            raise IssuerRequestRejected(
                error_code=UidaiRequestError.AADHAAR_REQUIRED.value
            )
        malformed = (
            not digits.isdigit()
            or len(digits) != AADHAAR_LENGTH
            or digits[0] in DISALLOWED_LEADING_DIGITS
        )
        if malformed:
            raise IssuerRequestRejected(
                error_code=UidaiRequestError.AADHAAR_MALFORMED.value
            )
        return digits
