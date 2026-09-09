import pytest

from document_catalog.storages.reference_data.issuer_service_specs import (
    ISSUER_SERVICE_SPECS,
)
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.issuer_check_constants import (
    ISSUER_CHECK_KEY,
    IssuerAnswerOutcome,
    IssuerUnreachableReason,
)
from document_scrutiny.domain.issuer_check import IssuerCheck
from document_scrutiny.dtos.issuer_answer_dtos import IssuerAnswerFactsDTO

DOCUMENT_ID = "document_1"
ITD_SERVICE = next(
    service for service in ISSUER_SERVICE_SPECS if service.issuer_service_id == "itd_pan"
)
SERVICE_NAME = "Income Tax PAN verification"
PAN_LABEL = "PAN"


def build_facts(
    outcome: str,
    disagreeing_fields=(),
    unreachable_reason=None,
    latency_ms=912,
    response_payload=None,
) -> IssuerAnswerFactsDTO:
    return IssuerAnswerFactsDTO(
        outcome=outcome,
        latency_ms=latency_ms,
        request_payload={"pan": "DQRPK4831L", "name": "SRINIVAS RAO KANDULA"},
        response_payload=response_payload,
        disagreeing_fields=tuple(disagreeing_fields),
        unreachable_reason=unreachable_reason,
    )


class TestIssuerCheck:
    def test_an_unreachable_issuer_is_unavailable_never_a_failure(self):
        # Arrange — AC7: the applicant is not at fault when the service is down
        facts = build_facts(
            outcome=IssuerAnswerOutcome.UNREACHABLE.value,
            unreachable_reason=IssuerUnreachableReason.TIMED_OUT.value,
            latency_ms=3000,
        )

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert check.status == CheckStatus.UNAVAILABLE.value
        assert check.title == f"{SERVICE_NAME} did not respond"
        assert "3000 ms" in check.detail
        assert "mark it verified by hand" in check.detail

    @pytest.mark.parametrize(
        "unreachable_reason, expected_phrase",
        [
            (IssuerUnreachableReason.CONNECTION_FAILED.value, "could not be reached"),
            (IssuerUnreachableReason.REFUSED_CREDENTIALS.value, "credentials"),
            (IssuerUnreachableReason.REJECTED_REQUEST.value, "rejected the request"),
            (IssuerUnreachableReason.SERVER_ERROR.value, "problem at its end"),
            (IssuerUnreachableReason.UNREADABLE_ANSWER.value, "could not read"),
        ],
    )
    def test_each_way_of_being_unreachable_says_what_happened(
        self, unreachable_reason, expected_phrase
    ):
        # Arrange
        facts = build_facts(
            outcome=IssuerAnswerOutcome.UNREACHABLE.value,
            unreachable_reason=unreachable_reason,
        )

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert check.status == CheckStatus.UNAVAILABLE.value
        assert expected_phrase in check.detail

    def test_a_department_that_has_no_record_of_the_pan_fails(self):
        # Arrange
        facts = build_facts(outcome=IssuerAnswerOutcome.NO_RECORD.value)

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert check.status == CheckStatus.FAIL.value
        assert check.title == f"{SERVICE_NAME} has no record of this PAN"

    def test_a_demographic_rejection_fails(self):
        # Arrange
        facts = build_facts(outcome=IssuerAnswerOutcome.NOT_MATCHED.value)

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert check.status == CheckStatus.FAIL.value
        assert check.title == f"{SERVICE_NAME} did not match"

    def test_a_disagreeing_name_warns_rather_than_claiming_confirmation(self):
        # Arrange — AC6: the verdict must not contradict the payload it discloses
        facts = build_facts(
            outcome=IssuerAnswerOutcome.PARTIAL_MATCH.value,
            disagreeing_fields=("name",),
            response_payload={"status": "VALID", "nameMatch": False, "dobMatch": True},
        )

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert check.status == CheckStatus.WARN.value
        assert check.title == f"{SERVICE_NAME} did not fully match"
        assert check.detail == (
            "The department holds this PAN but its record does not agree on the name."
        )

    def test_both_demographics_disagreeing_are_named_in_one_sentence(self):
        # Arrange
        facts = build_facts(
            outcome=IssuerAnswerOutcome.PARTIAL_MATCH.value,
            disagreeing_fields=("name", "dob"),
        )

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert check.detail == (
            "The department holds this PAN but its record does not agree on "
            "the name and the date of birth."
        )

    def test_a_confirmed_answer_passes(self):
        # Arrange — AC1
        facts = build_facts(outcome=IssuerAnswerOutcome.CONFIRMED.value)

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert check.status == CheckStatus.PASS.value
        assert check.title == f"{SERVICE_NAME} confirmed"

    def test_the_check_is_grouped_as_external_and_carries_no_field_key(self):
        # Arrange
        facts = build_facts(outcome=IssuerAnswerOutcome.CONFIRMED.value)

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert check.group == CheckGroup.EXTERNAL.value
        assert check.check_id == f"{DOCUMENT_ID}:{ISSUER_CHECK_KEY}"
        assert check.document_id == DOCUMENT_ID
        assert check.field_key is None

    def test_the_call_is_disclosed_so_the_officer_can_read_the_evidence(self):
        # Arrange
        response_payload = {"status": "VALID", "nameMatch": True, "dobMatch": True}
        facts = build_facts(
            outcome=IssuerAnswerOutcome.CONFIRMED.value,
            latency_ms=912,
            response_payload=response_payload,
        )

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        issuer_call = check.issuer_call
        assert issuer_call.issuer_service_id == "itd_pan"
        assert issuer_call.name == SERVICE_NAME
        assert issuer_call.endpoint == "POST /pan/verify"
        assert issuer_call.latency_ms == 912
        assert issuer_call.request_payload == {
            "pan": "DQRPK4831L",
            "name": "SRINIVAS RAO KANDULA",
        }
        assert issuer_call.response_payload == response_payload

    def test_an_outcome_this_app_does_not_know_is_treated_as_unavailable(self):
        # Arrange — a new issuer vocabulary must not be read as a pass
        facts = build_facts(outcome="something_new")

        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=facts,
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert check.status == CheckStatus.UNAVAILABLE.value


class TestEveryUnreachableReasonIsNamed:
    """A reason this system has not been taught must not borrow the timeout's
    wording — the officer would be told what happened, incorrectly."""

    def test_every_declared_reason_produces_its_own_explanation(self):
        # Arrange
        details = {}

        # Act
        for reason in IssuerUnreachableReason:
            details[reason.value] = IssuerCheck.build(
                document_id=DOCUMENT_ID,
                issuer_service=ITD_SERVICE,
                facts=IssuerAnswerFactsDTO(
                    outcome=IssuerAnswerOutcome.UNREACHABLE.value,
                    latency_ms=3000,
                    unreachable_reason=reason.value,
                ),
                document_type_label=PAN_LABEL,
            ).detail

        # Assert
        assert len(set(details.values())) == len(details)

    def test_a_reason_the_system_does_not_know_is_not_called_a_timeout(self):
        # Act
        check = IssuerCheck.build(
            document_id=DOCUMENT_ID,
            issuer_service=ITD_SERVICE,
            facts=IssuerAnswerFactsDTO(
                outcome=IssuerAnswerOutcome.UNREACHABLE.value,
                latency_ms=120,
                unreachable_reason="quantum_interference",
            ),
            document_type_label=PAN_LABEL,
        )

        # Assert
        assert "No response after" not in check.detail
        assert check.status == CheckStatus.UNAVAILABLE.value
