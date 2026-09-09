import abc
import json
import time
from typing import Any, Dict, Optional, Tuple

import httpx
from django.conf import settings

from document_verification.adapters.issuer_verification_interface import (
    IssuerVerificationInterface,
)
from document_verification.constants.verification_constants import (
    API_KEY_HEADER,
    DEMO_OUTCOME_HEADER,
    MILLISECONDS_PER_SECOND,
    IssuerOutcome,
    ServiceOverride,
    UnreachableReason,
)
from document_verification.dtos.verification_dtos import (
    IssuerAnswerDTO,
    VerifyDocumentRequestDTO,
)

UNAUTHORISED_STATUS = 401
CLIENT_ERROR_FLOOR = 400
SERVER_ERROR_FLOOR = 500


class HttpIssuerAdapter(IssuerVerificationInterface):
    """What every department call has in common: timing, and how it can fail.

    Held in one place on purpose. An officer has to be told "the department did
    not respond" in the same words whichever department it was, and a per-adapter
    copy of this mapping is how one issuer quietly starts reporting a refused
    credential as a mismatch the applicant has to answer for.

    A subclass supplies only what is genuinely its issuer's: the URL, the wire
    payload, and how to read the reply.
    """

    def __init__(self, transport: Optional[httpx.BaseTransport] = None):
        self.transport = transport

    def verify_document(self, request: VerifyDocumentRequestDTO) -> IssuerAnswerDTO:
        request_payload = self.build_request_payload(request=request)
        disclosed_payload = self.redact_disclosed(payload=request_payload)
        started_at = time.monotonic()
        try:
            response = self._send(request=request, request_payload=request_payload)
        except httpx.TimeoutException:
            return self._unreachable(
                reason=UnreachableReason.TIMED_OUT.value,
                request_payload=disclosed_payload,
                started_at=started_at,
            )
        except httpx.RequestError:
            return self._unreachable(
                reason=UnreachableReason.CONNECTION_FAILED.value,
                request_payload=disclosed_payload,
                started_at=started_at,
            )
        return self._read_response(
            response=response,
            request_payload=disclosed_payload,
            started_at=started_at,
        )

    def redact_disclosed(
        self, payload: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """What the officer is shown, in both directions.

        Applied to the request and to the department's answer, because an issuer
        that echoes an identifier back would otherwise put it on screen and into
        the scrutiny note by the back door. Identity for most departments; issuers
        holding a number that must not be written out override it.
        """
        if payload is None:
            return None
        return dict(payload)

    # ---- the subclass contract ----

    @property
    @abc.abstractmethod
    def verify_url(self) -> str:
        pass

    @property
    @abc.abstractmethod
    def request_timeout_seconds(self) -> float:
        pass

    @abc.abstractmethod
    def build_request_payload(
        self, request: VerifyDocumentRequestDTO
    ) -> Dict[str, Any]:
        pass

    @abc.abstractmethod
    def read_answer(
        self, body: Dict[str, Any]
    ) -> Tuple[Optional[str], Tuple[str, ...]]:
        pass

    # ---- shared machinery ----

    def _send(
        self, request: VerifyDocumentRequestDTO, request_payload: Dict[str, Any]
    ) -> httpx.Response:
        with httpx.Client(
            timeout=self.request_timeout_seconds, transport=self.transport
        ) as client:
            return client.post(
                self.verify_url,
                json=request_payload,
                headers=self.build_headers(request),
            )

    def build_headers(self, request: VerifyDocumentRequestDTO) -> Dict[str, str]:
        headers = {API_KEY_HEADER: settings.MOCK_ISSUER_API_KEY}
        if request.service_override != ServiceOverride.AUTO.value:
            headers[DEMO_OUTCOME_HEADER] = request.service_override
        return headers

    def _read_response(
        self,
        response: httpx.Response,
        request_payload: Dict[str, Any],
        started_at: float,
    ) -> IssuerAnswerDTO:
        body = self._read_body(response)
        disclosed_body = self.redact_disclosed(payload=body)
        transport_reason = self._transport_reason(response=response, body=body)
        if transport_reason is not None:
            return self._unreachable(
                reason=transport_reason,
                request_payload=request_payload,
                started_at=started_at,
                response_payload=disclosed_body,
            )

        # The verdict is read from the answer as it arrived; only what is shown is
        # redacted, so a mask can never change the outcome.
        outcome, disagreeing_fields = self.read_answer(body=body)
        if outcome is None:
            return self._unreachable(
                reason=UnreachableReason.UNREADABLE_ANSWER.value,
                request_payload=request_payload,
                started_at=started_at,
                response_payload=disclosed_body,
            )
        return IssuerAnswerDTO(
            outcome=outcome,
            latency_ms=self._elapsed_ms(started_at),
            request_payload=request_payload,
            response_payload=disclosed_body,
            disagreeing_fields=disagreeing_fields,
        )

    @staticmethod
    def _transport_reason(
        response: httpx.Response, body: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        if response.status_code == UNAUTHORISED_STATUS:
            return UnreachableReason.REFUSED_CREDENTIALS.value
        if response.status_code >= SERVER_ERROR_FLOOR:
            return UnreachableReason.SERVER_ERROR.value
        if response.status_code >= CLIENT_ERROR_FLOOR:
            return UnreachableReason.REJECTED_REQUEST.value
        if body is None:
            return UnreachableReason.UNREADABLE_ANSWER.value
        return None

    @staticmethod
    def _read_body(response: httpx.Response) -> Optional[Dict[str, Any]]:
        try:
            body = json.loads(response.content)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(body, dict):
            return None
        return body

    @classmethod
    def _unreachable(
        cls,
        reason: str,
        request_payload: Dict[str, Any],
        started_at: float,
        response_payload: Optional[Dict[str, Any]] = None,
    ) -> IssuerAnswerDTO:
        return IssuerAnswerDTO(
            outcome=IssuerOutcome.UNREACHABLE.value,
            latency_ms=cls._elapsed_ms(started_at),
            request_payload=request_payload,
            response_payload=response_payload,
            unreachable_reason=reason,
        )

    @staticmethod
    def _elapsed_ms(started_at: float) -> int:
        return int((time.monotonic() - started_at) * MILLISECONDS_PER_SECOND)
