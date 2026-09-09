import json
from unittest.mock import patch

import pytest
from django.urls import reverse

from mock_issuer_services.constants.itd_constants import (
    BAD_REQUEST_STATUS,
    REFERENCE_ID_PREFIX,
    SERVICE_UNAVAILABLE_STATUS,
    UNAUTHORISED_STATUS,
    DemoOutcome,
    ItdFailureReason,
    ItdRequestError,
    ItdServerError,
    ItdVerificationStatus,
)
from mock_issuer_services.tests.conftest import (
    CLEAN_DATE_OF_BIRTH,
    CLEAN_NAME,
    CLEAN_PAN,
    MISMATCH_DATE_OF_BIRTH,
    MISMATCH_PAN,
    MISMATCH_READ_NAME,
    UNHELD_PAN,
    VERIFY_URL_NAME,
    IssuerClientMock,
    build_payload,
    post_verify,
)

SLEEP_FOR = "mock_issuer_services.views.itd_pan_views.sleep_for"
METHOD_NOT_ALLOWED_STATUS = 405


class TestItdPanVerifyViewRejections(IssuerClientMock):
    def test_a_request_without_an_api_key_is_refused(self, client):
        # Arrange — the seam a real integration replaces carries a credential
        payload = build_payload()

        # Act
        response = post_verify(client, payload=payload, api_key=None)

        # Assert
        assert response.status_code == UNAUTHORISED_STATUS
        assert response.json()["errorCode"] == ItdRequestError.API_KEY_REQUIRED.value

    def test_a_request_with_the_wrong_api_key_is_refused(self, client):
        # Arrange
        payload = build_payload()

        # Act
        response = post_verify(client, payload=payload, api_key="not-the-key")

        # Assert
        assert response.status_code == UNAUTHORISED_STATUS
        assert response.json()["errorCode"] == ItdRequestError.API_KEY_INVALID.value

    def test_a_get_request_is_rejected(self, client):
        # Arrange
        url = reverse(VERIFY_URL_NAME)

        # Act
        response = client.get(url)

        # Assert
        assert response.status_code == METHOD_NOT_ALLOWED_STATUS

    @pytest.mark.parametrize("raw_body", ["{not json", "[1, 2, 3]", '"a string"'])
    def test_a_body_that_is_not_a_json_object_is_rejected(self, client, raw_body):
        # Arrange
        # Act
        response = post_verify(client, raw_body=raw_body)

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert response.json()["errorCode"] == ItdRequestError.INVALID_REQUEST_BODY.value

    @pytest.mark.parametrize("pan", ["", "   ", None, 12345, ["DQRPK4831L"]])
    def test_a_request_without_a_usable_pan_is_rejected(self, client, pan):
        # Arrange
        payload = {"pan": pan, "name": CLEAN_NAME}

        # Act
        response = post_verify(client, payload=payload)

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert response.json()["errorCode"] == ItdRequestError.PAN_REQUIRED.value

    @pytest.mark.parametrize("pan", ["NOTAPAN", "123456", "DQRPK4831", "DQRPK48311"])
    def test_a_pan_of_the_wrong_shape_is_told_apart_from_one_not_on_record(
        self, client, pan
    ):
        # Arrange
        payload = {"pan": pan, "name": CLEAN_NAME}

        # Act
        response = post_verify(client, payload=payload)

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert response.json()["errorCode"] == ItdRequestError.PAN_MALFORMED.value

    @pytest.mark.parametrize("name", ["", "   ", None, 42])
    def test_a_request_without_a_name_is_rejected_rather_than_reported_as_a_mismatch(
        self, client, name
    ):
        # Arrange — a demographic field the department was never given must not
        # come back looking like a disagreement
        payload = {"pan": CLEAN_PAN}
        if name is not None:
            payload["name"] = name

        # Act
        response = post_verify(client, payload=payload)

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert response.json()["errorCode"] == ItdRequestError.NAME_REQUIRED.value

    def test_an_unrecognised_demo_outcome_is_rejected_rather_than_ignored(self, client):
        # Arrange
        payload = build_payload()

        # Act
        response = post_verify(client, payload=payload, demo_outcome="explode")

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert response.json()["errorCode"] == ItdRequestError.UNKNOWN_DEMO_OUTCOME.value

    def test_forcing_an_outcome_is_refused_when_debug_is_off(self, client, settings):
        # Arrange — the demo control must not be reachable on a deployed host
        settings.DEBUG = False
        payload = build_payload()

        # Act
        response = post_verify(
            client, payload=payload, demo_outcome=DemoOutcome.PASS.value
        )

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"]
            == ItdRequestError.DEMO_OUTCOME_NOT_PERMITTED.value
        )

    def test_an_ordinary_request_still_works_when_debug_is_off(self, client, settings):
        # Arrange
        settings.DEBUG = False

        # Act
        response = post_verify(client, payload=build_payload())

        # Assert
        assert response.status_code == 200


class TestItdPanVerifyViewLookup(IssuerClientMock):
    def test_a_pan_the_department_has_no_record_of_is_reported_as_not_found(self, client):
        # Arrange — the issuer must never fabricate a match for an unknown PAN
        payload = build_payload(pan=UNHELD_PAN)

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["status"] == ItdVerificationStatus.NOT_FOUND.value
        assert body["reason"] == ItdFailureReason.NO_SUCH_PAN.value
        assert body["nameMatch"] is None
        assert body["dobMatch"] is None

    def test_a_matching_submission_is_reported_valid(self, client):
        # Arrange — AC1
        payload = build_payload()

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["status"] == ItdVerificationStatus.VALID.value
        assert body["nameMatch"] is True
        assert body["dobMatch"] is True
        assert body["aadhaarSeeded"] is True
        assert body["pan"] == CLEAN_PAN

    def test_the_department_never_discloses_the_name_it_holds(self, client):
        # Arrange — a verification answer is match booleans, not the record
        payload = build_payload(name="SOMEONE ELSE")

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["nameMatch"] is False
        assert CLEAN_NAME not in json.dumps(body)
        assert "registeredName" not in body

    def test_the_seeded_dropped_letter_produces_a_genuine_name_mismatch(self, client):
        # Arrange — AC6: 0377 reads SIDDIQI where the department holds SIDDIQUI
        payload = build_payload(
            pan=MISMATCH_PAN,
            name=MISMATCH_READ_NAME,
            date_of_birth=MISMATCH_DATE_OF_BIRTH,
        )

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["status"] == ItdVerificationStatus.VALID.value
        assert body["nameMatch"] is False
        assert body["dobMatch"] is True

    @pytest.mark.parametrize(
        "submitted_name",
        [
            "srinivas rao kandula",
            "  SRINIVAS   RAO  KANDULA  ",
            "Srinivas Rao Kandula",
            "SRINIVAS RAO KANDULA.",
            "SRINIVAS RAO, KANDULA",
            "SRINIVAS-RAO KANDULA",
        ],
    )
    def test_case_spacing_and_punctuation_do_not_defeat_the_departments_match(
        self, client, submitted_name
    ):
        # Arrange — the department normalises noise the way our own name check does,
        # so a punctuated read cannot warn at the issuer while passing at home
        payload = build_payload(name=submitted_name)

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["nameMatch"] is True

    def test_an_initial_where_the_full_name_is_registered_does_not_match(self, client):
        # Arrange — the department holds one name; abbreviation tolerance is our
        # side's judgement, not the department's
        payload = build_payload(name="S RAO KANDULA")

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["nameMatch"] is False

    def test_a_lowercase_pan_still_finds_the_record(self, client):
        # Arrange
        payload = build_payload(pan=CLEAN_PAN.lower())

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["status"] == ItdVerificationStatus.VALID.value
        assert body["pan"] == CLEAN_PAN

    def test_a_differing_date_of_birth_is_reported_unmatched(self, client):
        # Arrange
        payload = build_payload(date_of_birth="1978-08-14")

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["dobMatch"] is False

    @pytest.mark.parametrize(
        "submitted_date", ["1979-08-14", "14-08-1979", "14/08/1979"]
    )
    def test_a_date_written_day_first_is_understood(self, client, submitted_date):
        # Arrange — a PAN card prints dd/mm/yyyy and the officer sees dd-mm-yyyy
        payload = build_payload(date_of_birth=submitted_date)

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["dobMatch"] is True

    def test_a_date_of_birth_that_was_not_submitted_is_reported_as_not_asked(self, client):
        # Arrange — null, never false, so a pass is never disclosed beside a
        # date disagreement that did not happen
        payload = build_payload(date_of_birth=None)

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert body["dobMatch"] is None
        assert body["nameMatch"] is True

    def test_every_answer_carries_a_reference_that_is_not_the_subjects_pan(self, client):
        # Arrange
        payload = build_payload()

        # Act
        first = post_verify(client, payload=payload).json()["referenceId"]
        second = post_verify(client, payload=payload).json()["referenceId"]

        # Assert
        assert first.startswith(f"{REFERENCE_ID_PREFIX}/")
        assert CLEAN_PAN not in first
        assert first != second

    def test_the_answer_carries_no_field_the_status_already_says(self, client):
        # Arrange
        payload = build_payload()

        # Act
        body = post_verify(client, payload=payload).json()

        # Assert
        assert "found" not in body


class TestItdPanVerifyViewDemoOutcomes(IssuerClientMock):
    def test_forcing_a_pass_overrides_a_genuine_mismatch(self, client):
        # Arrange
        payload = build_payload(
            pan=MISMATCH_PAN,
            name=MISMATCH_READ_NAME,
            date_of_birth=MISMATCH_DATE_OF_BIRTH,
        )

        # Act
        body = post_verify(
            client, payload=payload, demo_outcome=DemoOutcome.PASS.value
        ).json()

        # Assert
        assert body["status"] == ItdVerificationStatus.VALID.value
        assert body["nameMatch"] is True
        assert body["dobMatch"] is True

    def test_forcing_a_failure_overrides_a_genuine_match(self, client):
        # Arrange
        payload = build_payload()

        # Act
        body = post_verify(
            client, payload=payload, demo_outcome=DemoOutcome.FAIL.value
        ).json()

        # Assert
        assert body["status"] == ItdVerificationStatus.NOT_MATCHED.value
        assert body["reason"] == ItdFailureReason.DEMOGRAPHIC_MISMATCH.value
        assert body["nameMatch"] is None

    @pytest.mark.parametrize(
        "demo_outcome, expected_status",
        [
            (DemoOutcome.PASS.value, ItdVerificationStatus.VALID.value),
            (DemoOutcome.FAIL.value, ItdVerificationStatus.NOT_MATCHED.value),
        ],
    )
    def test_a_forced_outcome_beats_the_record_lookup_either_way(
        self, client, demo_outcome, expected_status
    ):
        # Arrange — the operator forcing an outcome gets it even for an unheld PAN
        payload = build_payload(pan=UNHELD_PAN)

        # Act
        body = post_verify(
            client, payload=payload, demo_outcome=demo_outcome
        ).json()

        # Assert
        assert body["status"] == expected_status

    def test_forcing_a_server_error_gives_the_caller_a_non_timeout_failure(self, client):
        # Arrange — AC7 needs an unavailable path that is not a timeout
        payload = build_payload()

        # Act
        response = post_verify(
            client, payload=payload, demo_outcome=DemoOutcome.SERVER_ERROR.value
        )

        # Assert
        assert response.status_code == SERVICE_UNAVAILABLE_STATUS
        assert response.json()["errorCode"] == ItdServerError.UPSTREAM_UNAVAILABLE.value

    def test_forcing_a_timeout_waits_the_callers_budget_plus_the_margin(
        self, client, settings
    ):
        # Arrange
        settings.ITD_REQUEST_TIMEOUT_SECONDS = 3.0
        settings.MOCK_ISSUER_TIMEOUT_MARGIN_SECONDS = 1.0

        # Act
        with patch(SLEEP_FOR) as sleep_for:
            post_verify(
                client,
                payload=build_payload(),
                demo_outcome=DemoOutcome.TIMEOUT.value,
            )

        # Assert
        sleep_for.assert_called_once_with(seconds=4.0)

    def test_the_forced_timeout_latency_follows_a_changed_caller_budget(
        self, client, settings
    ):
        # Arrange — the latency is derived per call, so raising the budget at
        # runtime cannot leave the mock answering inside it
        settings.ITD_REQUEST_TIMEOUT_SECONDS = 10.0
        settings.MOCK_ISSUER_TIMEOUT_MARGIN_SECONDS = 0.5

        # Act
        with patch(SLEEP_FOR) as sleep_for:
            post_verify(
                client,
                payload=build_payload(),
                demo_outcome=DemoOutcome.TIMEOUT.value,
            )

        # Assert
        slept_seconds = sleep_for.call_args.kwargs["seconds"]
        assert slept_seconds > settings.ITD_REQUEST_TIMEOUT_SECONDS

    def test_the_normal_path_waits_the_departments_usual_latency(self, client, settings):
        # Arrange
        settings.MOCK_ISSUER_LATENCY_SECONDS = 0.9

        # Act
        with patch(SLEEP_FOR) as sleep_for:
            post_verify(client, payload=build_payload())

        # Assert
        sleep_for.assert_called_once_with(seconds=0.9)

    def test_asking_for_the_automatic_outcome_behaves_like_no_header_at_all(self, client):
        # Arrange
        payload = build_payload(
            pan=MISMATCH_PAN,
            name=MISMATCH_READ_NAME,
            date_of_birth=MISMATCH_DATE_OF_BIRTH,
        )

        # Act
        with_header = post_verify(
            client, payload=payload, demo_outcome=DemoOutcome.AUTO.value
        ).json()
        without_header = post_verify(client, payload=payload).json()

        # Assert
        assert with_header["status"] == without_header["status"]
        assert with_header["nameMatch"] == without_header["nameMatch"]
        assert with_header["dobMatch"] == without_header["dobMatch"]
