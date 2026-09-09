from typing import Any, Dict, Optional

import pytest
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from mock_issuer_services.constants.igrs_constants import (
    IgrsDeedStatus,
    IgrsFailureReason,
    IgrsRequestError,
    IgrsServerError,
)
from mock_issuer_services.constants.issuer_http_constants import (
    API_KEY_HEADER,
    BAD_REQUEST_STATUS,
    DEMO_OUTCOME_HEADER,
    SERVICE_UNAVAILABLE_STATUS,
    UNAUTHORISED_STATUS,
)
from mock_issuer_services.reference_data.igrs_deed_records import (
    IGRS_DEED_RECORDS_BY_DOCUMENT_NUMBER,
)
from mock_issuer_services.tests.conftest import DEMO_API_KEY

VERIFY_URL_NAME = "mock_igrs_look_up_deed"
METHOD_NOT_ALLOWED_STATUS = 405

DOCUMENT_NUMBER = "4821/2019"
CLAIMANT = "Srinivas Rao Kandula"
UNREGISTERED_DOCUMENT_NUMBER = "9999/1999"


def look_up(
    client: Client,
    doc_no: str = DOCUMENT_NUMBER,
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
        reverse(VERIFY_URL_NAME, kwargs={"doc_no": doc_no}),
        data=query if query is not None else {"name": CLAIMANT},
        headers=headers,
    )


class IgrsClientMock:
    @pytest.fixture
    def client(self) -> Client:
        return Client()

    @pytest.fixture(autouse=True)
    def instant_issuer(self, settings):
        settings.MOCK_ISSUER_LATENCY_SECONDS = 0
        settings.MOCK_ISSUER_TIMEOUT_MARGIN_SECONDS = 0
        settings.IGRS_REQUEST_TIMEOUT_SECONDS = 0
        settings.MOCK_ISSUER_API_KEY = DEMO_API_KEY
        settings.DEBUG = True


class TestIgrsLookupGuards(IgrsClientMock):
    def test_a_lookup_with_no_credential_is_refused(self, client):
        # Act
        response = look_up(client, api_key=None)

        # Assert
        assert response.status_code == UNAUTHORISED_STATUS
        assert response.json()["errorCode"] == IgrsRequestError.API_KEY_REQUIRED.value

    def test_a_lookup_with_the_wrong_credential_is_refused(self, client):
        # Act
        response = look_up(client, api_key="not-the-key")

        # Assert
        assert response.status_code == UNAUTHORISED_STATUS
        assert response.json()["errorCode"] == IgrsRequestError.API_KEY_INVALID.value

    def test_the_endpoint_answers_only_to_get(self, client):
        # Act
        response = client.post(
            reverse(VERIFY_URL_NAME, kwargs={"doc_no": DOCUMENT_NUMBER}),
            headers={API_KEY_HEADER: DEMO_API_KEY},
        )

        # Assert
        assert response.status_code == METHOD_NOT_ALLOWED_STATUS

    @pytest.mark.parametrize(
        "doc_no", ["4821", "4821/19", "abcd/2019", "4821-2019", "4821/2019/1"]
    )
    def test_a_number_that_could_not_be_a_registration_number_is_refused(
        self, client, doc_no
    ):
        # Act
        response = look_up(client, doc_no=doc_no)

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"]
            == IgrsRequestError.DOCUMENT_NUMBER_MALFORMED.value
        )

    def test_a_lookup_with_no_name_is_refused(self, client):
        # Act
        response = look_up(client, query={})

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert response.json()["errorCode"] == IgrsRequestError.NAME_REQUIRED.value

    def test_a_forced_outcome_is_refused_outside_debug(self, client, settings):
        # Arrange
        settings.DEBUG = False

        # Act
        response = look_up(client, demo_outcome="fail")

        # Assert
        assert response.status_code == BAD_REQUEST_STATUS
        assert (
            response.json()["errorCode"]
            == IgrsRequestError.DEMO_OUTCOME_NOT_PERMITTED.value
        )


class TestIgrsLookupAnswers(IgrsClientMock):
    def test_a_registered_deed_reports_the_parties_and_extent_on_record(self, client):
        # Act
        response = look_up(client)

        # Assert
        body = response.json()
        assert response.status_code == 200
        assert body["status"] == IgrsDeedStatus.REGISTERED.value
        assert body["sro"] == "Quthbullapur"
        assert body["executant"] == "PADMAVATHI RENTALA"
        assert body["claimant"] == "SRINIVAS RAO KANDULA"
        assert body["extent"] == "267 SQ.YDS"
        assert body["registrationDate"] == "2019-03-12"
        assert body["nameMatch"] is True

    def test_punctuation_and_case_in_a_name_do_not_count_as_disagreement(self, client):
        # Act
        response = look_up(client, query={"name": "  srinivas   rao kandula "})

        # Assert
        assert response.json()["nameMatch"] is True

    def test_a_deed_held_in_someone_elses_name_reports_the_disagreement(self, client):
        # Act
        response = look_up(client, query={"name": "Someone Else"})

        # Assert
        body = response.json()
        assert body["status"] == IgrsDeedStatus.REGISTERED.value
        assert body["nameMatch"] is False
        assert body["claimant"] == "SRINIVAS RAO KANDULA"

    def test_a_deed_the_register_does_not_hold_is_reported_as_no_such_deed(self, client):
        # Act
        response = look_up(client, doc_no=UNREGISTERED_DOCUMENT_NUMBER)

        # Assert
        body = response.json()
        assert body["status"] == IgrsDeedStatus.NOT_FOUND.value
        assert body["reason"] == IgrsFailureReason.NO_SUCH_DEED.value

    def test_every_deed_the_demo_ships_is_on_the_register(self, client):
        # Arrange — a demo where the registrar disowns its own deeds shows nothing
        for doc_no, record in IGRS_DEED_RECORDS_BY_DOCUMENT_NUMBER.items():
            # Act
            response = look_up(
                client, doc_no=doc_no, query={"name": record.claimant}
            )

            # Assert
            body = response.json()
            assert body["status"] == IgrsDeedStatus.REGISTERED.value
            assert body["nameMatch"] is True

    def test_the_register_holds_both_halves_of_every_chain(self, client):
        # Arrange — a sale deed's vendor must be the link document's claimant, or
        # there is no chain of title to trace
        pairs = [("4821/2019", "2210/2009"), ("6612/2021", "1105/2012"), ("3390/2020", "4471/2011")]

        for sale_deed_number, link_document_number in pairs:
            # Act
            sale_deed = IGRS_DEED_RECORDS_BY_DOCUMENT_NUMBER[sale_deed_number]
            link_document = IGRS_DEED_RECORDS_BY_DOCUMENT_NUMBER[link_document_number]

            # Assert
            assert sale_deed.executant == link_document.claimant


class TestIgrsForcedOutcomes(IgrsClientMock):
    def test_a_forced_pass_agrees_even_for_a_deed_it_does_not_hold(self, client):
        # Act
        response = look_up(
            client, doc_no=UNREGISTERED_DOCUMENT_NUMBER, demo_outcome="pass"
        )

        # Assert
        body = response.json()
        assert body["status"] == IgrsDeedStatus.REGISTERED.value
        assert body["nameMatch"] is True

    def test_a_forced_failure_reports_a_party_mismatch(self, client):
        # Act
        response = look_up(client, demo_outcome="fail")

        # Assert
        body = response.json()
        assert body["status"] == IgrsDeedStatus.NOT_MATCHED.value
        assert body["reason"] == IgrsFailureReason.PARTY_MISMATCH.value

    def test_a_forced_server_error_answers_unavailable(self, client):
        # Act
        response = look_up(client, demo_outcome="server_error")

        # Assert
        assert response.status_code == SERVICE_UNAVAILABLE_STATUS
        assert (
            response.json()["errorCode"] == IgrsServerError.IGRS_UNAVAILABLE.value
        )
