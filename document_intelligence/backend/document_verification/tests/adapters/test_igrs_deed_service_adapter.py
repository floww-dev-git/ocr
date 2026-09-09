import json

import httpx
import pytest

from document_verification.constants.verification_constants import (
    API_KEY_HEADER,
    DisagreeingField,
    IgrsStatus,
    IssuerOutcome,
    ServiceOverride,
    UnreachableReason,
)
from document_verification.dtos.verification_dtos import VerifyDocumentRequestDTO

DOCUMENT_NUMBER = "4821/2019"
PURCHASER = "Srinivas Rao Kandula"
SUB_REGISTRAR = "SRO Quthbullapur"


def build_request(
    service_override: str = ServiceOverride.AUTO.value, **overrides
) -> VerifyDocumentRequestDTO:
    lookup_values = {
        "docNo": DOCUMENT_NUMBER,
        "purchaser": PURCHASER,
        "sro": SUB_REGISTRAR,
        "vendor": "Padmavathi Rentala",
        "surveyNo": "118/2",
    }
    lookup_values.update(overrides)
    return VerifyDocumentRequestDTO(
        document_id="document_1",
        issuer_service_id="igrs",
        lookup_values={
            key: value for key, value in lookup_values.items() if value is not None
        },
        service_override=service_override,
    )


def build_adapter(handler):
    from document_verification.adapters.igrs_deed_service_adapter import (
        IgrsDeedServiceAdapter,
    )

    return IgrsDeedServiceAdapter(transport=httpx.MockTransport(handler))


def answer_with(body: dict, status_code: int = 200):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=body)

    return handler


def registered_deed(name_match: bool = True) -> dict:
    return {
        "docNo": DOCUMENT_NUMBER,
        "status": IgrsStatus.REGISTERED.value,
        "sro": "Quthbullapur",
        "executant": "PADMAVATHI RENTALA",
        "claimant": "SRINIVAS RAO KANDULA",
        "extent": "267 SQ.YDS",
        "registrationDate": "2019-03-12",
        "nameMatch": name_match,
    }


class TestIgrsAdapterIsALookup:
    def _capture(self, body=None):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["method"] = request.method
            captured["headers"] = dict(request.headers)
            return httpx.Response(200, json=body or registered_deed())

        return captured, handler

    def test_the_registration_number_keeps_its_slash_in_the_path(self, settings):
        # Arrange — the slash is part of the number, not a path separator
        settings.IGRS_VERIFY_URL = "http://issuer.example/igrs/deeds"
        captured, handler = self._capture()

        # Act
        build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["method"] == "GET"
        assert captured["url"].startswith(
            "http://issuer.example/igrs/deeds/4821/2019"
        )

    def test_the_purchaser_is_submitted_as_the_name_the_register_should_hold(self):
        # Arrange — the claimant is who the deed conveyed the property to
        captured, handler = self._capture()

        # Act
        answer = build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert answer.request_payload["name"] == PURCHASER
        assert f"name={PURCHASER.replace(' ', '+')}" in captured["url"]

    def test_the_disclosed_payload_names_the_deed_and_who_it_was_asked_about(self):
        # Act
        captured, handler = self._capture()
        answer = build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert answer.request_payload == {
            "docNo": DOCUMENT_NUMBER,
            "name": PURCHASER,
            "sro": SUB_REGISTRAR,
        }

    def test_a_sub_registrar_that_was_not_read_is_omitted(self):
        # Act
        captured, handler = self._capture()
        answer = build_adapter(handler).verify_document(request=build_request(sro=None))

        # Assert
        assert "sro" not in answer.request_payload

    def test_the_credential_is_sent_and_never_disclosed(self, settings):
        # Arrange
        settings.MOCK_ISSUER_API_KEY = "a-specific-key"
        captured, handler = self._capture()

        # Act
        answer = build_adapter(handler).verify_document(request=build_request())

        # Assert
        assert captured["headers"][API_KEY_HEADER.lower()] == "a-specific-key"
        assert "a-specific-key" not in json.dumps(answer.request_payload)


class TestIgrsAdapterAnswers:
    def test_a_deed_registered_to_the_purchaser_is_a_confirmation(self):
        # Arrange
        adapter = build_adapter(answer_with(registered_deed()))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.CONFIRMED.value
        assert answer.response_payload["executant"] == "PADMAVATHI RENTALA"
        assert answer.response_payload["extent"] == "267 SQ.YDS"

    def test_a_deed_registered_to_someone_else_is_a_partial_match(self):
        # Arrange — the registration is genuine; who holds it is the disagreement
        adapter = build_adapter(answer_with(registered_deed(name_match=False)))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert answer.disagreeing_fields == (DisagreeingField.NAME.value,)

    def test_a_deed_the_register_does_not_hold_is_reported_as_no_record(self):
        # Arrange
        adapter = build_adapter(
            answer_with({"status": IgrsStatus.NOT_FOUND.value, "reason": "NO_SUCH_DEED"})
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.NO_RECORD.value

    def test_a_party_rejection_is_reported_as_not_matched(self):
        # Arrange
        adapter = build_adapter(answer_with({"status": IgrsStatus.NOT_MATCHED.value}))

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.NOT_MATCHED.value

    def test_a_status_the_reader_does_not_know_is_unreadable_never_a_confirmation(self):
        # Arrange
        adapter = build_adapter(answer_with({"status": "PENDING_REGISTRATION"}))

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

    def test_a_registry_outage_is_unreachable_not_an_unregistered_deed(self):
        # Arrange — the difference matters: one is a wait, the other is a refusal
        adapter = build_adapter(
            answer_with({"errorCode": "IGRS_UNAVAILABLE"}, status_code=503)
        )

        # Act
        answer = adapter.verify_document(request=build_request())

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value
        assert answer.unreachable_reason == UnreachableReason.SERVER_ERROR.value
