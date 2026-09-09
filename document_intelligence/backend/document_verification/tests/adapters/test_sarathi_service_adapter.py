import json

import httpx
import pytest

from document_verification.constants.verification_constants import (
    API_KEY_HEADER,
    DEMO_OUTCOME_HEADER,
    DisagreeingField,
    IssuerOutcome,
    SarathiStatus,
    ServiceOverride,
    UnreachableReason,
)
from document_verification.dtos.verification_dtos import VerifyDocumentRequestDTO

SEEDED_LICENCE = "TS0920150012345"
HOLDER_NAME = "Srinivas Rao Kandula"
LICENCE_DATE_OF_BIRTH = "1978-08-14"


def build_request(
    service_override: str = ServiceOverride.AUTO.value, **overrides
) -> VerifyDocumentRequestDTO:
    lookup_values = {
        "dlNo": SEEDED_LICENCE,
        "name": HOLDER_NAME,
        "dob": LICENCE_DATE_OF_BIRTH,
    }
    lookup_values.update(overrides)
    return VerifyDocumentRequestDTO(
        document_id="document_1",
        issuer_service_id="sarathi",
        lookup_values={
            key: value for key, value in lookup_values.items() if value is not None
        },
        service_override=service_override,
    )


def build_adapter(handler):
    from document_verification.adapters.sarathi_service_adapter import (
        SarathiServiceAdapter,
    )

    return SarathiServiceAdapter(transport=httpx.MockTransport(handler))


def answer_with(body: dict, status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=body)

    return handler


def active_licence(name_match: bool = True, date_of_birth_match: bool = True) -> dict:
    return {
        "dlNo": SEEDED_LICENCE,
        "status": SarathiStatus.ACTIVE.value,
        "holder": "SRINIVAS RAO KANDULA",
        "dob": LICENCE_DATE_OF_BIRTH,
        "validUpto": "2035-06-30",
        "cov": ["LMV", "MCWG"],
        "nameMatch": name_match,
        "dobMatch": date_of_birth_match,
    }


class TestSarathiServiceAdapterIsALookup:
    def _capture(self, body=None):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["method"] = request.method
            captured["headers"] = dict(request.headers)
            captured["content"] = request.content
            return httpx.Response(200, json=body or active_licence())

        return captured, handler

    def test_the_licence_number_is_looked_up_in_the_path_not_posted(self, settings):
        # Arrange
        settings.SARATHI_VERIFY_URL = "http://issuer.example/sarathi/dl"
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["method"] == "GET"
        assert captured["url"].startswith(
            f"http://issuer.example/sarathi/dl/{SEEDED_LICENCE}"
        )
        assert captured["content"] == b""

    def test_the_demographics_to_compare_ride_as_query_parameters(self, settings):
        # Arrange
        settings.SARATHI_VERIFY_URL = "http://issuer.example/sarathi/dl"
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert f"name={HOLDER_NAME.replace(' ', '+')}" in captured["url"]
        assert f"dob={LICENCE_DATE_OF_BIRTH}" in captured["url"]
        assert "dlNo=" not in captured["url"]

    def test_the_disclosed_payload_names_everything_that_was_asked(self):
        # Arrange — the officer needs to see what was asked, not the URL shape
        captured, handler = self._capture()

        # Act
        answer = build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert answer.request_payload == {
            "dlNo": SEEDED_LICENCE,
            "name": HOLDER_NAME,
            "dob": LICENCE_DATE_OF_BIRTH,
        }

    def test_a_date_of_birth_that_was_not_read_is_omitted(self):
        # Arrange
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request(dob=None))

        # Assert
        assert "dob=" not in captured["url"]

    def test_the_credential_is_sent_as_a_header_and_never_disclosed(self, settings):
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
            request=build_request(service_override=ServiceOverride.TIMEOUT.value)
        )

        # Assert
        assert captured["headers"][DEMO_OUTCOME_HEADER.lower()] == "timeout"


class TestSarathiServiceAdapterAnswers:
    def test_an_active_licence_agreeing_throughout_is_a_confirmation(self):
        # Arrange
        adapter = build_adapter(answer_with(active_licence()))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.CONFIRMED.value
        assert answer.disagreeing_fields == ()
        assert answer.response_payload["cov"] == ["LMV", "MCWG"]

    def test_an_active_licence_with_a_disagreeing_name_is_a_partial_match(self):
        # Arrange — the department vouches for the licence, not for the form
        adapter = build_adapter(answer_with(active_licence(name_match=False)))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert answer.disagreeing_fields == (DisagreeingField.NAME.value,)

    def test_a_disagreeing_date_of_birth_is_a_partial_match(self):
        # Arrange
        adapter = build_adapter(
            answer_with(active_licence(date_of_birth_match=False))
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert answer.disagreeing_fields == (DisagreeingField.DATE_OF_BIRTH.value,)

    def test_a_date_of_birth_the_department_was_not_asked_about_is_not_a_disagreement(
        self,
    ):
        # Arrange
        adapter = build_adapter(
            answer_with(active_licence(date_of_birth_match=None))
        )

        # Act
        answer = adapter.verify_document(request=build_request(dob=None))

        # Assert
        assert answer.outcome == IssuerOutcome.CONFIRMED.value

    def test_a_licence_the_department_does_not_hold_is_reported_as_no_record(self):
        # Arrange
        adapter = build_adapter(
            answer_with(
                {
                    "status": SarathiStatus.NOT_FOUND.value,
                    "reason": "NO_SUCH_LICENCE",
                }
            )
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.NO_RECORD.value

    def test_a_holder_rejection_is_reported_as_not_matched(self):
        # Arrange
        adapter = build_adapter(
            answer_with({"status": SarathiStatus.NOT_MATCHED.value})
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.NOT_MATCHED.value

    def test_a_status_the_reader_does_not_know_is_unreadable_never_a_confirmation(self):
        # Arrange
        adapter = build_adapter(answer_with({"status": "SUSPENDED"}))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.UNREADABLE_ANSWER.value

    @pytest.mark.parametrize(
        "raised,expected_reason",
        [
            (httpx.ReadTimeout, UnreachableReason.TIMED_OUT.value),
            (httpx.ConnectError, UnreachableReason.CONNECTION_FAILED.value),
        ],
    )
    def test_transport_failures_map_the_same_way_as_every_other_department(
        self, raised, expected_reason
    ):
        # Arrange
        def handler(request: httpx.Request) -> httpx.Response:
            raise raised("no", request=request)

        adapter = build_adapter(handler)

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == expected_reason

    def test_a_department_outage_is_unreachable_not_the_applicants_fault(self):
        # Arrange
        adapter = build_adapter(
            answer_with({"errorCode": "SARATHI_UNAVAILABLE"}, status_code=503)
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.SERVER_ERROR.value
