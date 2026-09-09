import json

import httpx
import pytest

from document_verification.constants.verification_constants import (
    API_KEY_HEADER,
    DEMO_OUTCOME_HEADER,
    DisagreeingField,
    IssuerOutcome,
    ServiceOverride,
    UidaiStatus,
    UnreachableReason,
)
from document_verification.dtos.verification_dtos import VerifyDocumentRequestDTO

CLEAN_AADHAAR = "731655204821"
CLEAN_NAME = "Srinivas Rao Kandula"
CLEAN_DATE_OF_BIRTH = "1979-08-14"
CLEAN_GENDER = "Male"


def build_request(
    service_override: str = ServiceOverride.AUTO.value, **overrides
) -> VerifyDocumentRequestDTO:
    lookup_values = {
        "aadhaarNo": CLEAN_AADHAAR,
        "name": CLEAN_NAME,
        "dob": CLEAN_DATE_OF_BIRTH,
        "gender": CLEAN_GENDER,
    }
    lookup_values.update(overrides)
    return VerifyDocumentRequestDTO(
        document_id="document_1",
        issuer_service_id="uidai",
        lookup_values={
            key: value for key, value in lookup_values.items() if value is not None
        },
        service_override=service_override,
    )


def build_adapter(handler):
    from document_verification.adapters.uidai_service_adapter import (
        UidaiServiceAdapter,
    )

    return UidaiServiceAdapter(transport=httpx.MockTransport(handler))


def answer_with(body: dict, status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=body)

    return handler


class TestUidaiServiceAdapterAnswers:
    def test_every_demographic_agreeing_is_a_confirmation(self):
        # Arrange
        adapter = build_adapter(
            answer_with(
                {
                    "status": UidaiStatus.MATCHED.value,
                    "matched": ["name", "dob", "gender"],
                    "txn": "UID-ABC1234567",
                }
            )
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.CONFIRMED.value
        assert answer.disagreeing_fields == ()

    def test_a_demographic_uidai_did_not_confirm_is_a_partial_match(self):
        # Arrange — UIDAI reports what agreed, so silence is disagreement
        adapter = build_adapter(
            answer_with(
                {"status": UidaiStatus.MATCHED.value, "matched": ["dob", "gender"]}
            )
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert answer.disagreeing_fields == (DisagreeingField.NAME.value,)

    def test_an_absent_matched_list_is_unreadable_never_a_confirmation(self):
        # Arrange — reading a missing field as consent would confirm an unchecked card
        adapter = build_adapter(answer_with({"status": UidaiStatus.MATCHED.value}))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.UNREADABLE_ANSWER.value

    def test_a_number_uidai_does_not_hold_is_reported_as_no_record(self):
        # Arrange
        adapter = build_adapter(
            answer_with(
                {
                    "status": UidaiStatus.NOT_FOUND.value,
                    "matched": [],
                    "reason": "NO_SUCH_AADHAAR",
                }
            )
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.NO_RECORD.value

    def test_a_demographic_rejection_is_reported_as_not_matched(self):
        # Arrange
        adapter = build_adapter(
            answer_with({"status": UidaiStatus.NOT_MATCHED.value, "matched": []})
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.NOT_MATCHED.value

    def test_a_timeout_is_reported_unreachable_like_every_other_department(self):
        # Arrange — the shared failure mapping must not vary by issuer
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("budget exceeded", request=request)

        adapter = build_adapter(handler)

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.TIMED_OUT.value

    def test_an_auth_server_failure_is_unreachable_not_the_applicants_fault(self):
        # Arrange
        adapter = build_adapter(
            answer_with({"errorCode": "AUTH_SERVER_UNAVAILABLE"}, status_code=503)
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.SERVER_ERROR.value


class TestUidaiServiceAdapterRequest:
    def _capture(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = dict(request.headers)
            captured["body"] = json.loads(request.content)
            captured["url"] = str(request.url)
            return httpx.Response(
                200,
                json={
                    "status": UidaiStatus.MATCHED.value,
                    "matched": ["name", "dob", "gender"],
                },
            )

        return captured, handler

    def test_the_full_number_is_sent_because_it_is_the_lookup_key(self):
        # Arrange
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["body"]["aadhaarNo"] == CLEAN_AADHAAR

    def test_the_disclosed_payload_masks_the_number_the_officer_will_copy_out(self):
        # Arrange — this payload is shown in the Checks panel and copied into the note
        captured, handler = self._capture()

        # Act
        answer = build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert answer.request_payload["aadhaarNo"] == "XXXX XXXX 4821"
        assert CLEAN_AADHAAR not in json.dumps(answer.request_payload)

    def test_the_demographics_read_from_the_card_are_all_submitted(self):
        # Arrange
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["body"] == {
            "aadhaarNo": CLEAN_AADHAAR,
            "name": CLEAN_NAME,
            "dob": CLEAN_DATE_OF_BIRTH,
            "gender": CLEAN_GENDER,
        }

    @pytest.mark.parametrize("omitted_key", ["dob", "gender"])
    def test_a_demographic_that_was_not_read_is_omitted_rather_than_sent_empty(
        self, omitted_key
    ):
        # Arrange
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(
            request=build_request(**{omitted_key: None})
        )

        # Assert
        assert omitted_key not in captured["body"]

    def test_the_credential_never_reaches_the_disclosed_payload(self, settings):
        # Arrange
        settings.MOCK_ISSUER_API_KEY = "a-specific-key"
        captured, handler = self._capture()

        # Act
        answer = build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["headers"][API_KEY_HEADER.lower()] == "a-specific-key"
        assert "a-specific-key" not in json.dumps(answer.request_payload)

    def test_a_forced_outcome_is_passed_to_the_department_as_a_header(self):
        # Arrange
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(
            request=build_request(service_override=ServiceOverride.FAIL.value)
        )

        # Assert
        assert captured["headers"][DEMO_OUTCOME_HEADER.lower()] == "fail"

    def test_the_configured_uidai_endpoint_is_called(self, settings):
        # Arrange
        settings.UIDAI_VERIFY_URL = "http://issuer.example/uidai/aadhaar/verify"
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["url"] == "http://issuer.example/uidai/aadhaar/verify"


class TestUidaiDisclosureIsRedactedBothWays:
    def test_the_number_uidai_echoes_back_is_masked_in_the_disclosed_answer(self):
        # Arrange — UIDAI returns the number it was asked about, and that answer is
        # shown in the Checks panel and copied into the scrutiny note
        adapter = build_adapter(
            answer_with(
                {
                    "aadhaarNo": CLEAN_AADHAAR,
                    "status": UidaiStatus.MATCHED.value,
                    "matched": ["name", "dob", "gender"],
                    "txn": "UID-AA6BB63D34",
                }
            )
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.response_payload["aadhaarNo"] == "XXXX XXXX 4821"
        assert CLEAN_AADHAAR not in json.dumps(answer.response_payload)
        assert answer.response_payload["txn"] == "UID-AA6BB63D34"

    def test_masking_the_answer_never_changes_the_verdict(self):
        # Arrange — the outcome is read from the answer as it arrived
        adapter = build_adapter(
            answer_with(
                {
                    "aadhaarNo": CLEAN_AADHAAR,
                    "status": UidaiStatus.MATCHED.value,
                    "matched": ["dob", "gender"],
                }
            )
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert answer.disagreeing_fields == (DisagreeingField.NAME.value,)
        assert answer.response_payload["aadhaarNo"] == "XXXX XXXX 4821"

    def test_an_error_body_is_redacted_too(self):
        # Arrange
        adapter = build_adapter(
            answer_with(
                {"aadhaarNo": CLEAN_AADHAAR, "errorCode": "AUTH_SERVER_UNAVAILABLE"},
                status_code=503,
            )
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert CLEAN_AADHAAR not in json.dumps(answer.response_payload)

    def test_a_department_holding_nothing_sensitive_discloses_its_answer_unchanged(self):
        # Arrange — the redaction is per issuer, not a blanket rewrite
        from document_verification.adapters.itd_pan_service_adapter import (
            ItdPanServiceAdapter,
        )

        body = {"status": "VALID", "nameMatch": True, "dobMatch": True, "pan": "DQRPK4831L"}
        adapter = ItdPanServiceAdapter(
            transport=httpx.MockTransport(answer_with(body))
        )

        # Act
        answer = adapter.verify_document(
            request=VerifyDocumentRequestDTO(
                document_id="document_1",
                issuer_service_id="itd_pan",
                lookup_values={"pan": "DQRPK4831L", "name": "SRINIVAS RAO KANDULA"},
            )
        )

        # Assert
        assert answer.response_payload == body
