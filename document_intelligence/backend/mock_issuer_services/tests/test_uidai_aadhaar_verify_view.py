import json
from typing import Any, Dict, Optional

import pytest
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from mock_issuer_services.constants.issuer_http_constants import (
    API_KEY_HEADER,
    BAD_REQUEST_STATUS,
    DEMO_OUTCOME_HEADER,
    SERVICE_UNAVAILABLE_STATUS,
    UNAUTHORISED_STATUS,
)
from mock_issuer_services.constants.uidai_constants import (
    UidaiAuthStatus,
    UidaiFailureReason,
    UidaiRequestError,
    UidaiServerError,
)
from mock_issuer_services.tests.conftest import DEMO_API_KEY

VERIFY_URL_NAME = "mock_uidai_verify_aadhaar"
METHOD_NOT_ALLOWED_STATUS = 405

CLEAN_AADHAAR = "731655204821"
CLEAN_NAME = "Srinivas Rao Kandula"
CLEAN_DATE_OF_BIRTH = "1979-08-14"
CLEAN_GENDER = "Male"
UNHELD_AADHAAR = "999888777666"


def build_payload(
    aadhaar_number: Optional[str] = CLEAN_AADHAAR,
    name: Optional[str] = CLEAN_NAME,
    date_of_birth: Optional[str] = CLEAN_DATE_OF_BIRTH,
    gender: Optional[str] = CLEAN_GENDER,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if aadhaar_number is not None:
        payload["aadhaarNo"] = aadhaar_number
    if name is not None:
        payload["name"] = name
    if date_of_birth is not None:
        payload["dob"] = date_of_birth
    if gender is not None:
        payload["gender"] = gender
    return payload


def post_verify(
    client: Client,
    payload: Optional[Dict[str, Any]] = None,
    demo_outcome: Optional[str] = None,
    raw_body: Optional[str] = None,
    api_key: Optional[str] = DEMO_API_KEY,
) -> HttpResponse:
    headers: Dict[str, str] = {}
    if api_key is not None:
        headers[API_KEY_HEADER] = api_key
    if demo_outcome is not None:
        headers[DEMO_OUTCOME_HEADER] = demo_outcome
    body = (
        raw_body
        if raw_body is not None
        else json.dumps(payload if payload is not None else build_payload())
    )
    return client.post(
        reverse(VERIFY_URL_NAME),
        data=body,
        content_type="application/json",
        headers=headers,
    )


class UidaiClientMock:
    @pytest.fixture
    def client(self) -> Client:
        return Client()

    @pytest.fixture(autouse=True)
    def instant_issuer(self, settings):
        settings.MOCK_ISSUER_LATENCY_SECONDS = 0
        settings.MOCK_ISSUER_TIMEOUT_MARGIN_SECONDS = 0
        settings.UIDAI_REQUEST_TIMEOUT_SECONDS = 0
        settings.MOCK_ISSUER_API_KEY = DEMO_API_KEY
        settings.DEBUG = True


class TestUidaiVerifyRequestGuards(UidaiClientMock):
    def test_a_request_with_no_credential_is_refused(self, client):
        # Act
        response = post_verify(client, api_key=None)

        # Assert
        assert response.status_code == UNAUTHORISED_STATUS
        assert (
            response.json()["errorCode"] == UidaiRequestError.API_KEY_REQUIRED.value
        )

    def test_a_request_with_the_wrong_credential_is_refused(self, client):
        # Act
        response = post_verify(client, api_key="not-the-key")

        # Assert
        assert response.status_code == UNAUTHORISED_STATUS
        assert response.json()["errorCode"] == UidaiRequestError.API_KEY_INVALID.value

    def test_the_endpoint_answers_only_to_post(self, client):
        # Act
        response = client.get(reverse(VERIFY_URL_NAME))

        # Assert
        assert response.status_code == METHOD_NOT_ALLOWED_STATUS

    def test_a_body_that_is_not_json_is_refused(self, client):
        # Act
        response = post_verify(client, raw_body="not json at all")

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"]
            == UidaiRequestError.INVALID_REQUEST_BODY.value
        )

    def test_a_request_with_no_number_is_refused(self, client):
        # Act
        response = post_verify(client, payload=build_payload(aadhaar_number=None))

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"] == UidaiRequestError.AADHAAR_REQUIRED.value
        )

    @pytest.mark.parametrize(
        "aadhaar_number", ["73165520482", "7316552048211", "73165520482X", "031655204821"]
    )
    def test_a_number_that_could_not_be_an_aadhaar_is_refused(
        self, client, aadhaar_number
    ):
        # Act
        response = post_verify(
            client, payload=build_payload(aadhaar_number=aadhaar_number)
        )

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"] == UidaiRequestError.AADHAAR_MALFORMED.value
        )

    def test_the_printed_grouping_is_accepted(self, client):
        # Arrange — the card prints three groups of four
        # Act
        response = post_verify(
            client, payload=build_payload(aadhaar_number="7316 5520 4821")
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == UidaiAuthStatus.MATCHED.value

    def test_a_request_with_no_name_is_refused(self, client):
        # Act
        response = post_verify(client, payload=build_payload(name=None))

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert response.json()["errorCode"] == UidaiRequestError.NAME_REQUIRED.value

    def test_an_unknown_forced_outcome_is_refused(self, client):
        # Act
        response = post_verify(client, demo_outcome="explode")

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"]
            == UidaiRequestError.UNKNOWN_DEMO_OUTCOME.value
        )

    def test_a_forced_outcome_is_refused_outside_debug(self, client, settings):
        # Arrange — forcing an answer is a demo affordance, not a feature
        settings.DEBUG = False

        # Act
        response = post_verify(client, demo_outcome="fail")

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"]
            == UidaiRequestError.DEMO_OUTCOME_NOT_PERMITTED.value
        )


class TestUidaiVerifyAnswers(UidaiClientMock):
    def test_a_number_uidai_holds_with_agreeing_demographics_matches_all_three(
        self, client
    ):
        # Act
        response = post_verify(client)

        # Assert
        body = response.json()
        assert response.status_code == 200
        assert body["status"] == UidaiAuthStatus.MATCHED.value
        assert sorted(body["matched"]) == ["dob", "gender", "name"]
        assert body["aadhaarNo"] == CLEAN_AADHAAR
        assert body["txn"].startswith("UID-")

    def test_a_disagreeing_name_is_reported_by_its_absence(self, client):
        # Arrange — UIDAI answers with what agreed, not with what failed
        # Act
        response = post_verify(
            client, payload=build_payload(name="Srinivas Rao Kandala")
        )

        # Assert
        body = response.json()
        assert body["status"] == UidaiAuthStatus.MATCHED.value
        assert "name" not in body["matched"]
        assert sorted(body["matched"]) == ["dob", "gender"]

    def test_punctuation_and_case_in_a_name_do_not_count_as_disagreement(self, client):
        # Act
        response = post_verify(
            client, payload=build_payload(name="  srinivas   rao kandula ")
        )

        # Assert
        assert "name" in response.json()["matched"]

    def test_a_day_first_date_of_birth_is_understood(self, client):
        # Act
        response = post_verify(client, payload=build_payload(date_of_birth="14-08-1979"))

        # Assert
        assert "dob" in response.json()["matched"]

    def test_a_disagreeing_date_of_birth_is_reported_by_its_absence(self, client):
        # Act
        response = post_verify(client, payload=build_payload(date_of_birth="1978-08-14"))

        # Assert
        assert "dob" not in response.json()["matched"]

    def test_a_disagreeing_gender_is_reported_by_its_absence(self, client):
        # Act
        response = post_verify(client, payload=build_payload(gender="Female"))

        # Assert
        assert "gender" not in response.json()["matched"]

    def test_a_demographic_that_was_not_submitted_is_not_reported_as_disagreeing(
        self, client
    ):
        # Arrange — UIDAI only answers on what it was asked
        # Act
        response = post_verify(
            client, payload=build_payload(date_of_birth=None, gender=None)
        )

        # Assert
        assert sorted(response.json()["matched"]) == ["dob", "gender", "name"]

    def test_a_number_uidai_does_not_hold_is_reported_as_no_such_aadhaar(self, client):
        # Act
        response = post_verify(
            client, payload=build_payload(aadhaar_number=UNHELD_AADHAAR)
        )

        # Assert
        body = response.json()
        assert body["status"] == UidaiAuthStatus.NOT_FOUND.value
        assert body["matched"] == []
        assert body["reason"] == UidaiFailureReason.NO_SUCH_AADHAAR.value

    def test_every_seeded_application_number_is_held(self, client):
        # Arrange — the demo depends on all three confirming
        for aadhaar_number in ("731655204821", "409322107754", "551809326604"):
            # Act
            response = post_verify(
                client,
                payload=build_payload(
                    aadhaar_number=aadhaar_number, date_of_birth=None, gender=None
                ),
            )

            # Assert
            assert response.json()["status"] == UidaiAuthStatus.MATCHED.value


class TestUidaiForcedOutcomes(UidaiClientMock):
    def test_a_forced_pass_matches_everything_even_for_a_number_it_does_not_hold(
        self, client
    ):
        # Act
        response = post_verify(
            client,
            payload=build_payload(aadhaar_number=UNHELD_AADHAAR),
            demo_outcome="pass",
        )

        # Assert
        body = response.json()
        assert body["status"] == UidaiAuthStatus.MATCHED.value
        assert sorted(body["matched"]) == ["dob", "gender", "name"]

    def test_a_forced_failure_reports_a_demographic_mismatch(self, client):
        # Act
        response = post_verify(client, demo_outcome="fail")

        # Assert
        body = response.json()
        assert body["status"] == UidaiAuthStatus.NOT_MATCHED.value
        assert body["reason"] == UidaiFailureReason.DEMOGRAPHIC_MISMATCH.value

    def test_a_forced_server_error_answers_unavailable(self, client):
        # Act
        response = post_verify(client, demo_outcome="server_error")

        # Assert
        assert response.status_code == SERVICE_UNAVAILABLE_STATUS
        assert (
            response.json()["errorCode"]
            == UidaiServerError.AUTH_SERVER_UNAVAILABLE.value
        )
