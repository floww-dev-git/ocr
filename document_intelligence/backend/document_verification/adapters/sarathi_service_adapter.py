from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import httpx
from django.conf import settings

from document_verification.adapters.http_issuer_adapter import HttpIssuerAdapter
from document_verification.domain.sarathi_answer_reader import SarathiAnswerReader
from document_verification.dtos.verification_dtos import VerifyDocumentRequestDTO

LICENCE_FIELD_KEY = "dlNo"
NAME_FIELD_KEY = "name"
DATE_OF_BIRTH_FIELD_KEY = "dob"


class SarathiServiceAdapter(HttpIssuerAdapter):
    """The Transport Department's driving licence check.

    A lookup rather than a submission: the licence number is part of the URL and the
    demographics to compare against ride as query parameters. The disclosed payload
    still names all three, because what the officer needs to see is what was asked,
    not how the request happened to be shaped.
    """

    @property
    def verify_url(self) -> str:
        return settings.SARATHI_VERIFY_URL

    @property
    def request_timeout_seconds(self) -> float:
        return float(settings.SARATHI_REQUEST_TIMEOUT_SECONDS)

    def build_request_payload(
        self, request: VerifyDocumentRequestDTO
    ) -> Dict[str, Any]:
        read_values = request.lookup_values
        payload: Dict[str, Any] = {
            LICENCE_FIELD_KEY: read_values.get(LICENCE_FIELD_KEY, ""),
            NAME_FIELD_KEY: read_values.get(NAME_FIELD_KEY, ""),
        }
        date_of_birth = read_values.get(DATE_OF_BIRTH_FIELD_KEY)
        if date_of_birth:
            payload[DATE_OF_BIRTH_FIELD_KEY] = date_of_birth
        return payload

    def _send(
        self, request: VerifyDocumentRequestDTO, request_payload: Dict[str, Any]
    ) -> httpx.Response:
        licence_number = str(request_payload.get(LICENCE_FIELD_KEY, ""))
        query = {
            key: value
            for key, value in request_payload.items()
            if key != LICENCE_FIELD_KEY
        }
        with httpx.Client(
            timeout=self.request_timeout_seconds, transport=self.transport
        ) as client:
            return client.get(
                f"{self.verify_url}/{quote(licence_number, safe='')}",
                params=query,
                headers=self.build_headers(request),
            )

    def read_answer(
        self, body: Dict[str, Any]
    ) -> Tuple[Optional[str], Tuple[str, ...]]:
        return SarathiAnswerReader.read(body=body)
