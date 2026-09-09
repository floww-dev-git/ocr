import json

import httpx
import pytest

from document_verification.constants.verification_constants import (
    API_KEY_HEADER,
    DEMO_OUTCOME_HEADER,
    DisagreeingField,
    IssuerOutcome,
    IssuerStatus,
    ServiceOverride,
    UnreachableReason,
)
from document_verification.dtos.verification_dtos import VerifyDocumentRequestDTO

CLEAN_PAN = "DQRPK4831L"
CLEAN_NAME = "SRINIVAS RAO KANDULA"
CLEAN_DATE_OF_BIRTH = "1979-08-14"


def build_request(
    service_override: str = ServiceOverride.AUTO.value,
    date_of_birth: str = CLEAN_DATE_OF_BIRTH,
) -> VerifyDocumentRequestDTO:
    lookup_values = {"pan": CLEAN_PAN, "name": CLEAN_NAME}
    if date_of_birth is not None:
        lookup_values["dob"] = date_of_birth
    return VerifyDocumentRequestDTO(
        document_id="document_1",
        issuer_service_id="itd_pan",
        lookup_values=lookup_values,
        service_override=service_override,
    )


def build_adapter(handler):
    from document_verification.adapters.itd_pan_service_adapter import (
        ItdPanServiceAdapter,
    )

    return ItdPanServiceAdapter(transport=httpx.MockTransport(handler))


def answer_with(body: dict, status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=body)

    return handler


class TestItdPanServiceAdapterUnreachable:
    def test_a_timeout_is_reported_unreachable_without_raising(self):
        # Arrange — AC7
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("budget exceeded", request=request)

        adapter = build_adapter(handler)

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.TIMED_OUT.value
        assert answer.response_payload is None

    def test_a_refused_connection_is_reported_unreachable(self):
        # Arrange
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route to host", request=request)

        adapter = build_adapter(handler)

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.CONNECTION_FAILED.value

    def test_a_server_error_is_reported_unreachable_not_failed(self):
        # Arrange — AC7 needs an unavailable path that is not a timeout
        adapter = build_adapter(
            answer_with({"errorCode": "UPSTREAM_UNAVAILABLE"}, status_code=503)
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.SERVER_ERROR.value
        assert answer.response_payload == {"errorCode": "UPSTREAM_UNAVAILABLE"}

    def test_a_refused_credential_is_reported_unreachable_not_failed(self):
        # Arrange — an authentication problem is ours, never the applicant's
        adapter = build_adapter(answer_with({"errorCode": "API_KEY_INVALID"}, status_code=401))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.REFUSED_CREDENTIALS.value

    def test_a_rejected_request_is_reported_unreachable(self):
        # Arrange
        adapter = build_adapter(answer_with({"errorCode": "PAN_MALFORMED"}, status_code=400))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.REJECTED_REQUEST.value

    def test_an_answer_that_is_not_json_is_reported_unreachable(self):
        # Arrange
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"<html>gateway</html>")

        adapter = build_adapter(handler)

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.UNREADABLE_ANSWER.value

    def test_an_answer_the_reader_cannot_interpret_is_reported_unreachable(self):
        # Arrange
        adapter = build_adapter(answer_with({"status": "MAYBE"}))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.UNREADABLE_ANSWER.value


class TestItdPanServiceAdapterAnswers:
    def test_a_confirmed_answer_carries_the_outcome_and_the_payload(self):
        # Arrange — AC1
        body = {
            "status": IssuerStatus.VALID.value,
            "nameMatch": True,
            "dobMatch": True,
            "referenceId": "ITD/ABC123",
        }
        adapter = build_adapter(answer_with(body))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.CONFIRMED.value
        assert answer.response_payload == body
        assert answer.unreachable_reason is None

    def test_a_disagreeing_name_is_a_partial_match(self):
        # Arrange — AC6
        adapter = build_adapter(
            answer_with(
                {"status": IssuerStatus.VALID.value, "nameMatch": False, "dobMatch": True}
            )
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert answer.disagreeing_fields == (DisagreeingField.NAME.value,)

    def test_the_latency_of_the_call_is_recorded(self):
        # Arrange
        adapter = build_adapter(
            answer_with({"status": IssuerStatus.VALID.value, "nameMatch": True})
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.latency_ms >= 0
        assert isinstance(answer.latency_ms, int)


class TestItdPanServiceAdapterRequest:
    def _capture(self, body=None):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["headers"] = dict(request.headers)
            captured["body"] = json.loads(request.content)
            captured["url"] = str(request.url)
            return httpx.Response(
                200,
                json=body
                or {"status": IssuerStatus.VALID.value, "nameMatch": True, "dobMatch": True},
            )

        return captured, handler

    def test_the_credential_is_sent_as_a_header(self, settings):
        # Arrange
        settings.MOCK_ISSUER_API_KEY = "a-specific-key"
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["headers"][API_KEY_HEADER.lower()] == "a-specific-key"

    def test_the_credential_never_reaches_the_disclosed_payload(self, settings):
        # Arrange — the officer sees this payload; a key must never ride along
        settings.MOCK_ISSUER_API_KEY = "a-specific-key"
        captured, handler = self._capture()

        # Act
        answer = build_adapter(handler).verify_document(request=build_request())

        # Assert
        disclosed = json.dumps(answer.request_payload)
        assert "a-specific-key" not in disclosed
        assert API_KEY_HEADER not in answer.request_payload
        assert set(answer.request_payload) == {"pan", "name", "dob"}

    def test_the_demographics_read_from_the_card_are_all_submitted(self):
        # Arrange
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["body"] == {
            "pan": CLEAN_PAN,
            "name": CLEAN_NAME,
            "dob": CLEAN_DATE_OF_BIRTH,
        }

    def test_a_date_of_birth_that_was_not_read_is_omitted_rather_than_sent_empty(self):
        # Arrange
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(
            request=build_request(date_of_birth=None)
        )

        # Assert
        assert "dob" not in captured["body"]

    def test_no_demo_header_is_sent_when_the_officer_asked_for_the_automatic_outcome(self):
        # Arrange
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert DEMO_OUTCOME_HEADER.lower() not in captured["headers"]

    @pytest.mark.parametrize(
        "service_override",
        [
            ServiceOverride.PASS.value,
            ServiceOverride.FAIL.value,
            ServiceOverride.TIMEOUT.value,
            ServiceOverride.SERVER_ERROR.value,
        ],
    )
    def test_a_forced_outcome_is_passed_to_the_issuer_as_a_header(
        self, service_override
    ):
        # Arrange
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(
            request=build_request(service_override=service_override)
        )

        # Assert
        assert captured["headers"][DEMO_OUTCOME_HEADER.lower()] == service_override

    def test_the_configured_issuer_endpoint_is_called(self, settings):
        # Arrange
        settings.ITD_PAN_VERIFY_URL = "http://issuer.example/itd/pan/verify"
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["url"] == "http://issuer.example/itd/pan/verify"
