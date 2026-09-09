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
from mock_issuer_services.constants.sarathi_constants import (
    SarathiFailureReason,
    SarathiLicenceStatus,
    SarathiRequestError,
    SarathiServerError,
)
from mock_issuer_services.tests.conftest import DEMO_API_KEY

VERIFY_URL_NAME = "mock_sarathi_look_up_licence"
METHOD_NOT_ALLOWED_STATUS = 405

SEEDED_LICENCE = "TS0920150012345"
HOLDER_NAME = "Srinivas Rao Kandula"
LICENCE_DATE_OF_BIRTH = "1978-08-14"
UNHELD_LICENCE = "KA0520180099999"


def look_up(
    client: Client,
    licence_number: str = SEEDED_LICENCE,
    query: Optional[Dict[str, Any]] = None,
    demo_outcome: Optional[str] = None,
    api_key: Optional[str] = DEMO_API_KEY,
) -> HttpResponse:
    headers: Dict[str, str] = {}
    if api_key is not None:
        headers[API_KEY_HEADER] = api_key
    if demo_outcome is not None:
        headers[DEMO_OUTCOME_HEADER] = demo_outcome
    return client.get(
        reverse(VERIFY_URL_NAME, kwargs={"licence_number": licence_number}),
        data=query if query is not None else {"name": HOLDER_NAME, "dob": LICENCE_DATE_OF_BIRTH},
        headers=headers,
    )


class SarathiClientMock:
    @pytest.fixture
    def client(self) -> Client:
        return Client()

    @pytest.fixture(autouse=True)
    def instant_issuer(self, settings):
        settings.MOCK_ISSUER_LATENCY_SECONDS = 0
        settings.MOCK_ISSUER_TIMEOUT_MARGIN_SECONDS = 0
        settings.SARATHI_REQUEST_TIMEOUT_SECONDS = 0
        settings.MOCK_ISSUER_API_KEY = DEMO_API_KEY
        settings.DEBUG = True


class TestSarathiLookupGuards(SarathiClientMock):
    def test_a_lookup_with_no_credential_is_refused(self, client):
        # Act
        response = look_up(client, api_key=None)

        # Assert
        assert response.status_code == UNAUTHORISED_STATUS
        assert (
            response.json()["errorCode"] == SarathiRequestError.API_KEY_REQUIRED.value
        )

    def test_a_lookup_with_the_wrong_credential_is_refused(self, client):
        # Act
        response = look_up(client, api_key="not-the-key")

        # Assert
        assert response.status_code == UNAUTHORISED_STATUS
        assert (
            response.json()["errorCode"] == SarathiRequestError.API_KEY_INVALID.value
        )

    def test_the_endpoint_answers_only_to_get(self, client):
        # Act
        response = client.post(
            reverse(VERIFY_URL_NAME, kwargs={"licence_number": SEEDED_LICENCE}),
            headers={API_KEY_HEADER: DEMO_API_KEY},
        )

        # Assert
        assert response.status_code == METHOD_NOT_ALLOWED_STATUS

    @pytest.mark.parametrize(
        "licence_number", ["TS09", "TS092015001234567", "DQRPK4831L", "731655204821345"]
    )
    def test_a_number_that_could_not_be_a_licence_is_refused(
        self, client, licence_number
    ):
        # Act
        response = look_up(client, licence_number=licence_number)

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"]
            == SarathiRequestError.LICENCE_MALFORMED.value
        )

    def test_a_licence_printed_with_separators_is_accepted(self, client):
        # Act
        response = look_up(client, licence_number="TS-09-20150012345")

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == SarathiLicenceStatus.ACTIVE.value

    def test_a_lookup_with_no_name_is_refused(self, client):
        # Act
        response = look_up(client, query={"dob": LICENCE_DATE_OF_BIRTH})

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert response.json()["errorCode"] == SarathiRequestError.NAME_REQUIRED.value

    def test_a_forced_outcome_is_refused_outside_debug(self, client, settings):
        # Arrange
        settings.DEBUG = False

        # Act
        response = look_up(client, demo_outcome="fail")

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"]
            == SarathiRequestError.DEMO_OUTCOME_NOT_PERMITTED.value
        )


class TestSarathiLookupAnswers(SarathiClientMock):
    def test_the_seeded_licence_is_active_and_reports_what_the_department_holds(
        self, client
    ):
        # Act
        response = look_up(client)

        # Assert
        body = response.json()
        assert response.status_code == 200
        assert body["status"] == SarathiLicenceStatus.ACTIVE.value
        assert body["holder"] == "SRINIVAS RAO KANDULA"
        assert body["dob"] == LICENCE_DATE_OF_BIRTH
        assert body["validUpto"] == "2035-06-30"
        assert body["cov"] == ["LMV", "MCWG"]
        assert body["nameMatch"] is True
        assert body["dobMatch"] is True

    def test_the_department_agrees_with_the_licence_not_the_application_form(
        self, client
    ):
        # Arrange — the application says 1979; the licence and the registry say 1978
        # Act
        agreeing = look_up(
            client, query={"name": HOLDER_NAME, "dob": "1978-08-14"}
        ).json()
        disagreeing = look_up(
            client, query={"name": HOLDER_NAME, "dob": "1979-08-14"}
        ).json()

        # Assert
        assert agreeing["dobMatch"] is True
        assert disagreeing["dobMatch"] is False

    def test_a_day_first_date_is_understood(self, client):
        # Act
        response = look_up(client, query={"name": HOLDER_NAME, "dob": "14-08-1978"})

        # Assert
        assert response.json()["dobMatch"] is True

    def test_punctuation_and_case_in_a_name_do_not_count_as_disagreement(self, client):
        # Act
        response = look_up(
            client, query={"name": "  srinivas   rao kandula ", "dob": LICENCE_DATE_OF_BIRTH}
        )

        # Assert
        assert response.json()["nameMatch"] is True

    def test_a_disagreeing_name_is_reported(self, client):
        # Act
        response = look_up(
            client, query={"name": "Someone Else", "dob": LICENCE_DATE_OF_BIRTH}
        )

        # Assert
        assert response.json()["nameMatch"] is False

    def test_a_date_of_birth_that_was_not_asked_about_is_answered_with_null(
        self, client
    ):
        # Act
        response = look_up(client, query={"name": HOLDER_NAME})

        # Assert
        assert response.json()["dobMatch"] is None

    def test_a_licence_the_department_does_not_hold_is_reported_as_no_such_licence(
        self, client
    ):
        # Act
        response = look_up(client, licence_number=UNHELD_LICENCE)

        # Assert
        body = response.json()
        assert body["status"] == SarathiLicenceStatus.NOT_FOUND.value
        assert body["reason"] == SarathiFailureReason.NO_SUCH_LICENCE.value


class TestSarathiForcedOutcomes(SarathiClientMock):
    def test_a_forced_pass_agrees_even_for_a_licence_it_does_not_hold(self, client):
        # Act
        response = look_up(client, licence_number=UNHELD_LICENCE, demo_outcome="pass")

        # Assert
        body = response.json()
        assert body["status"] == SarathiLicenceStatus.ACTIVE.value
        assert body["nameMatch"] is True

    def test_a_forced_failure_reports_a_holder_mismatch(self, client):
        # Act
        response = look_up(client, demo_outcome="fail")

        # Assert
        body = response.json()
        assert body["status"] == SarathiLicenceStatus.NOT_MATCHED.value
        assert body["reason"] == SarathiFailureReason.HOLDER_MISMATCH.value

    def test_a_forced_server_error_answers_unavailable(self, client):
        # Act
        response = look_up(client, demo_outcome="server_error")

        # Assert
        assert response.status_code == SERVICE_UNAVAILABLE_STATUS
        assert (
            response.json()["errorCode"]
            == SarathiServerError.SARATHI_UNAVAILABLE.value
        )
