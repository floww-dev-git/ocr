from typing import Any, Dict, Optional, Tuple
from urllib.parse import quote

import httpx
from django.conf import settings

from document_verification.adapters.http_issuer_adapter import HttpIssuerAdapter
from document_verification.domain.igrs_answer_reader import IgrsAnswerReader
from document_verification.dtos.verification_dtos import VerifyDocumentRequestDTO

DOCUMENT_NUMBER_FIELD_KEY = "docNo"
SUB_REGISTRAR_FIELD_KEY = "sro"
PURCHASER_FIELD_KEY = "purchaser"
NAME_FIELD_KEY = "name"


class IgrsDeedServiceAdapter(HttpIssuerAdapter):
    """The registrar's lookup of a registered deed.

    Serves both a sale deed and a link document: the question is the same either
    way, because a registration number identifies a deed regardless of which of the
    two roles it is playing in this application.
    """

    @property
    def verify_url(self) -> str:
        return settings.IGRS_VERIFY_URL

    @property
    def request_timeout_seconds(self) -> float:
        return float(settings.IGRS_REQUEST_TIMEOUT_SECONDS)

    def build_request_payload(
        self, request: VerifyDocumentRequestDTO
    ) -> Dict[str, Any]:
        read_values = request.lookup_values
        payload: Dict[str, Any] = {
            DOCUMENT_NUMBER_FIELD_KEY: read_values.get(DOCUMENT_NUMBER_FIELD_KEY, ""),
            # The purchaser is who the deed conveyed the property to, which is the
            # name the register should hold as the claimant.
            NAME_FIELD_KEY: read_values.get(PURCHASER_FIELD_KEY, ""),
        }
        sub_registrar = read_values.get(SUB_REGISTRAR_FIELD_KEY)
        if sub_registrar:
            payload[SUB_REGISTRAR_FIELD_KEY] = sub_registrar
        return payload

    def _send(
        self, request: VerifyDocumentRequestDTO, request_payload: Dict[str, Any]
    ) -> httpx.Response:
        doc_no = str(request_payload.get(DOCUMENT_NUMBER_FIELD_KEY, ""))
        query = {
            key: value
            for key, value in request_payload.items()
            if key != DOCUMENT_NUMBER_FIELD_KEY
        }
        with httpx.Client(
            timeout=self.request_timeout_seconds, transport=self.transport
        ) as client:
            # A registration number contains a slash, which is part of the number
            # rather than a path separator, so it is kept as one path segment.
            return client.get(
                f"{self.verify_url}/{quote(doc_no, safe='/')}",
                params=query,
                headers=self.build_headers(request),
            )

    def read_answer(
        self, body: Dict[str, Any]
    ) -> Tuple[Optional[str], Tuple[str, ...]]:
        return IgrsAnswerReader.read(body=body)
