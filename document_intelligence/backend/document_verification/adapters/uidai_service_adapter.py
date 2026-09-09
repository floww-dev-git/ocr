from typing import Any, Dict, Optional, Tuple

from django.conf import settings

from document_verification.adapters.http_issuer_adapter import HttpIssuerAdapter
from document_verification.domain.uidai_answer_reader import UidaiAnswerReader
from document_verification.dtos.verification_dtos import VerifyDocumentRequestDTO

AADHAAR_FIELD_KEY = "aadhaarNo"
NAME_FIELD_KEY = "name"
DATE_OF_BIRTH_FIELD_KEY = "dob"
GENDER_FIELD_KEY = "gender"

MASKED_AADHAAR_LENGTH = 12
VISIBLE_TAIL_LENGTH = 4
MASK_TEMPLATE = "XXXX XXXX {tail}"


class UidaiServiceAdapter(HttpIssuerAdapter):
    """UIDAI's Aadhaar demographic authentication."""

    @property
    def verify_url(self) -> str:
        return settings.UIDAI_VERIFY_URL

    @property
    def request_timeout_seconds(self) -> float:
        return float(settings.UIDAI_REQUEST_TIMEOUT_SECONDS)

    def build_request_payload(
        self, request: VerifyDocumentRequestDTO
    ) -> Dict[str, Any]:
        read_values = request.lookup_values
        payload: Dict[str, Any] = {
            AADHAAR_FIELD_KEY: read_values.get(AADHAAR_FIELD_KEY, ""),
            NAME_FIELD_KEY: read_values.get(NAME_FIELD_KEY, ""),
        }
        for optional_key in (DATE_OF_BIRTH_FIELD_KEY, GENDER_FIELD_KEY):
            value = read_values.get(optional_key)
            if value:
                payload[optional_key] = value
        return payload

    def redact_disclosed(
        self, payload: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        # The number goes to UIDAI in full — it is the lookup key — but what the
        # officer is shown, and what lands in the scrutiny note, is masked. UIDAI
        # echoes the number back in its answer, so the answer is masked too. The
        # mask is written as a mask so nobody mistakes it for the wire content.
        if payload is None:
            return None
        disclosed = dict(payload)
        if AADHAAR_FIELD_KEY in disclosed:
            disclosed[AADHAAR_FIELD_KEY] = self._mask(
                str(disclosed[AADHAAR_FIELD_KEY])
            )
        return disclosed

    def read_answer(
        self, body: Dict[str, Any]
    ) -> Tuple[Optional[str], Tuple[str, ...]]:
        return UidaiAnswerReader.read(body=body)

    @staticmethod
    def _mask(aadhaar_number: str) -> str:
        digits = "".join(aadhaar_number.split())
        if len(digits) != MASKED_AADHAAR_LENGTH:
            return digits
        return MASK_TEMPLATE.format(tail=digits[-VISIBLE_TAIL_LENGTH:])
