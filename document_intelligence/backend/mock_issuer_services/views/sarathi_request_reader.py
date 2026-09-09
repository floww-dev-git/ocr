import re
from dataclasses import dataclass
from typing import Optional

from django.http import HttpRequest

from mock_issuer_services.constants.issuer_http_constants import DemoOutcome
from mock_issuer_services.constants.sarathi_constants import SarathiRequestError
from mock_issuer_services.views.issuer_request_reader import (
    IssuerRequestReader,
    IssuerRequestRejected,
    RequestErrorCodes,
)

# Thirteen or fourteen digits: the RTO block is two digits in most offices and
# three in some, so a licence this department issues is 15 or 16 characters. Stated
# independently of the scrutiny side's own rule, as ADR-004 requires — the mock does
# not share a constant with the system querying it.
_LICENCE_PATTERN = re.compile(r"[A-Z]{2}[0-9]{13,14}")

SARATHI_ERROR_CODES = RequestErrorCodes(
    api_key_required=SarathiRequestError.API_KEY_REQUIRED.value,
    api_key_invalid=SarathiRequestError.API_KEY_INVALID.value,
    invalid_request_body=SarathiRequestError.INVALID_REQUEST_BODY.value,
    name_required=SarathiRequestError.NAME_REQUIRED.value,
    unknown_demo_outcome=SarathiRequestError.UNKNOWN_DEMO_OUTCOME.value,
    demo_outcome_not_permitted=SarathiRequestError.DEMO_OUTCOME_NOT_PERMITTED.value,
)


@dataclass(frozen=True)
class SarathiLookupRequestDTO:
    licence_number: str
    name: str
    date_of_birth: Optional[str]
    demo_outcome: DemoOutcome


class SarathiRequestReader:
    """Sarathi is looked up, not posted to: the licence number is in the path.

    The demographics to compare against ride as query parameters, which is why this
    reader takes them from the query string rather than a body.
    """

    @classmethod
    def read(
        cls, request: HttpRequest, licence_number: str
    ) -> SarathiLookupRequestDTO:
        IssuerRequestReader.check_api_key(request=request, codes=SARATHI_ERROR_CODES)
        demo_outcome = IssuerRequestReader.read_demo_outcome(
            request=request, codes=SARATHI_ERROR_CODES
        )
        query = request.GET.dict()
        return SarathiLookupRequestDTO(
            licence_number=cls._read_licence_number(licence_number),
            name=IssuerRequestReader.read_name(
                payload=query, codes=SARATHI_ERROR_CODES
            ),
            date_of_birth=IssuerRequestReader.read_text(query, "dob") or None,
            demo_outcome=demo_outcome,
        )

    @staticmethod
    def _read_licence_number(licence_number: Optional[str]) -> str:
        # Printed with spaces or hyphens as often as without, so both are accepted.
        candidate = re.sub(r"[\s-]", "", str(licence_number or "")).upper()
        if not candidate:
            raise IssuerRequestRejected(
                error_code=SarathiRequestError.LICENCE_REQUIRED.value
            )
        if _LICENCE_PATTERN.fullmatch(candidate) is None:
            raise IssuerRequestRejected(
                error_code=SarathiRequestError.LICENCE_MALFORMED.value
            )
        return candidate
