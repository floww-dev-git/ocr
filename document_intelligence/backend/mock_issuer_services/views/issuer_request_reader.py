import json
from dataclasses import dataclass
from typing import Any, Dict

from django.conf import settings
from django.http import HttpRequest, JsonResponse

from common.exceptions.base import BaseExceptionClass
from mock_issuer_services.constants.issuer_http_constants import (
    API_KEY_HEADER,
    BAD_REQUEST_STATUS,
    DEMO_OUTCOME_HEADER,
    UNAUTHORISED_STATUS,
    DemoOutcome,
)


@dataclass(frozen=True)
class RequestErrorCodes:
    """The error codes one issuer answers with for the failures every issuer shares.

    Passed in rather than shared outright so each department keeps its own error
    vocabulary in its own enum, while the checks themselves stay in one place.
    """

    api_key_required: str
    api_key_invalid: str
    invalid_request_body: str
    name_required: str
    unknown_demo_outcome: str
    demo_outcome_not_permitted: str


class IssuerRequestRejected(BaseExceptionClass):
    def __init__(self, error_code: str, authentication: bool = False):
        self.error_code = error_code
        self.authentication = authentication


class IssuerRequestReader:
    """The parts of reading a department's request that are the same everywhere.

    Kept in one place because the credential check and the demo-outcome guard are
    the two things here that must not drift: a department that quietly stops
    checking its API key, or that honours a forced outcome outside DEBUG, is a hole
    rather than a demo.
    """

    @staticmethod
    def check_api_key(request: HttpRequest, codes: RequestErrorCodes) -> None:
        submitted_key = request.headers.get(API_KEY_HEADER)
        if submitted_key is None:
            raise IssuerRequestRejected(
                error_code=codes.api_key_required, authentication=True
            )
        if submitted_key != settings.MOCK_ISSUER_API_KEY:
            raise IssuerRequestRejected(
                error_code=codes.api_key_invalid, authentication=True
            )

    @staticmethod
    def read_demo_outcome(
        request: HttpRequest, codes: RequestErrorCodes
    ) -> DemoOutcome:
        requested = request.headers.get(DEMO_OUTCOME_HEADER)
        if requested is None:
            return DemoOutcome.AUTO
        if not settings.DEBUG:
            # Forcing an outcome is a demo affordance. Outside DEBUG it would let a
            # caller dictate a department's answer.
            raise IssuerRequestRejected(error_code=codes.demo_outcome_not_permitted)
        try:
            return DemoOutcome(requested)
        except ValueError as error:
            raise IssuerRequestRejected(
                error_code=codes.unknown_demo_outcome
            ) from error

    @staticmethod
    def read_payload(request: HttpRequest, codes: RequestErrorCodes) -> Dict[str, Any]:
        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError as error:
            raise IssuerRequestRejected(
                error_code=codes.invalid_request_body
            ) from error
        if not isinstance(payload, dict):
            raise IssuerRequestRejected(error_code=codes.invalid_request_body)
        return payload

    @classmethod
    def read_name(cls, payload: Dict[str, Any], codes: RequestErrorCodes) -> str:
        name = cls.read_text(payload, "name")
        if not name:
            raise IssuerRequestRejected(error_code=codes.name_required)
        return name

    @staticmethod
    def read_text(payload: Dict[str, Any], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str):
            return ""
        return value.strip()


def build_rejection_response(rejection: IssuerRequestRejected) -> JsonResponse:
    status = UNAUTHORISED_STATUS if rejection.authentication else BAD_REQUEST_STATUS
    return JsonResponse({"errorCode": rejection.error_code}, status=status)
