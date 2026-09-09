from typing import Any, Dict, Optional, Tuple

from django.conf import settings

from document_verification.adapters.http_issuer_adapter import HttpIssuerAdapter
from document_verification.domain.itd_pan_answer_reader import ItdPanAnswerReader
from document_verification.dtos.verification_dtos import VerifyDocumentRequestDTO

PAN_FIELD_KEY = "pan"
NAME_FIELD_KEY = "name"
DATE_OF_BIRTH_FIELD_KEY = "dob"


class ItdPanServiceAdapter(HttpIssuerAdapter):
    """The Income Tax Department's PAN verification service."""

    @property
    def verify_url(self) -> str:
        return settings.ITD_PAN_VERIFY_URL

    @property
    def request_timeout_seconds(self) -> float:
        return float(settings.ITD_REQUEST_TIMEOUT_SECONDS)

    def build_request_payload(
        self, request: VerifyDocumentRequestDTO
    ) -> Dict[str, Any]:
        read_values = request.lookup_values
        payload: Dict[str, Any] = {
            PAN_FIELD_KEY: read_values.get(PAN_FIELD_KEY, ""),
            NAME_FIELD_KEY: read_values.get(NAME_FIELD_KEY, ""),
        }
        date_of_birth = read_values.get(DATE_OF_BIRTH_FIELD_KEY)
        if date_of_birth:
            payload[DATE_OF_BIRTH_FIELD_KEY] = date_of_birth
        return payload

    def read_answer(
        self, body: Dict[str, Any]
    ) -> Tuple[Optional[str], Tuple[str, ...]]:
        return ItdPanAnswerReader.read(body=body)
