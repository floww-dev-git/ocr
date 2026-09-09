import re
from dataclasses import dataclass
from typing import Optional

from django.http import HttpRequest

from mock_issuer_services.constants.igrs_constants import IgrsRequestError
from mock_issuer_services.constants.issuer_http_constants import DemoOutcome
from mock_issuer_services.views.issuer_request_reader import (
    IssuerRequestReader,
    IssuerRequestRejected,
    RequestErrorCodes,
)

# A registration number reads as a serial and a year: '4821/2019'.
_DOCUMENT_NUMBER_PATTERN = re.compile(r"\d{1,6}/\d{4}")

IGRS_ERROR_CODES = RequestErrorCodes(
    api_key_required=IgrsRequestError.API_KEY_REQUIRED.value,
    api_key_invalid=IgrsRequestError.API_KEY_INVALID.value,
    invalid_request_body=IgrsRequestError.INVALID_REQUEST_BODY.value,
    name_required=IgrsRequestError.NAME_REQUIRED.value,
    unknown_demo_outcome=IgrsRequestError.UNKNOWN_DEMO_OUTCOME.value,
    demo_outcome_not_permitted=IgrsRequestError.DEMO_OUTCOME_NOT_PERMITTED.value,
)


@dataclass(frozen=True)
class IgrsLookupRequestDTO:
    doc_no: str
    name: str
    sro: Optional[str]
    demo_outcome: DemoOutcome


class IgrsRequestReader:
    """The registrar is looked up by document number, which sits in the path."""

    @classmethod
    def read(cls, request: HttpRequest, doc_no: str) -> IgrsLookupRequestDTO:
        IssuerRequestReader.check_api_key(request=request, codes=IGRS_ERROR_CODES)
        demo_outcome = IssuerRequestReader.read_demo_outcome(
            request=request, codes=IGRS_ERROR_CODES
        )
        query = request.GET.dict()
        return IgrsLookupRequestDTO(
            doc_no=cls._read_document_number(doc_no),
            name=IssuerRequestReader.read_name(
                payload=query, codes=IGRS_ERROR_CODES
            ),
            sro=IssuerRequestReader.read_text(query, "sro") or None,
            demo_outcome=demo_outcome,
        )

    @staticmethod
    def _read_document_number(doc_no: Optional[str]) -> str:
        candidate = re.sub(r"\s", "", str(doc_no or ""))
        if not candidate:
            raise IssuerRequestRejected(
                error_code=IgrsRequestError.DOCUMENT_NUMBER_REQUIRED.value
            )
        if _DOCUMENT_NUMBER_PATTERN.fullmatch(candidate) is None:
            raise IssuerRequestRejected(
                error_code=IgrsRequestError.DOCUMENT_NUMBER_MALFORMED.value
            )
        return candidate
