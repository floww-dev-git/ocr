import dataclasses

from document_verification.constants.verification_constants import (
    DisagreeingField,
    IssuerOutcome,
    UnreachableReason,
)
from document_verification.dtos.verification_dtos import IssuerAnswerDTO
from document_scrutiny.constants.issuer_check_constants import (
    DISAGREEING_FIELD_LABELS,
    IssuerAnswerOutcome,
    IssuerUnreachableReason,
)
from document_scrutiny.dtos.issuer_answer_dtos import IssuerAnswerFactsDTO


class TestIssuerVocabularyContract:
    def test_every_outcome_the_verification_app_can_report_is_understood_here(self):
        # Arrange — app isolation means this app restates the vocabulary, so the
        # two sides have to be pinned together
        reported = {outcome.value for outcome in IssuerOutcome}

        # Act
        understood = {outcome.value for outcome in IssuerAnswerOutcome}

        # Assert
        assert understood == reported

    def test_every_unreachable_reason_the_verification_app_can_report_is_understood(self):
        # Arrange
        reported = {reason.value for reason in UnreachableReason}

        # Act
        understood = {reason.value for reason in IssuerUnreachableReason}

        # Assert
        assert understood == reported

    def test_every_field_the_issuer_can_disagree_on_has_a_label(self):
        # Arrange
        reported = {field_key.value for field_key in DisagreeingField}

        # Act
        labelled = set(DISAGREEING_FIELD_LABELS)

        # Assert
        assert labelled == reported

    def test_the_facts_this_app_reads_match_the_answer_the_other_app_returns(self):
        # Arrange — the answer crosses the boundary and is read as facts here
        answer_fields = {field.name for field in dataclasses.fields(IssuerAnswerDTO)}

        # Act
        facts_fields = {field.name for field in dataclasses.fields(IssuerAnswerFactsDTO)}

        # Assert
        assert facts_fields == answer_fields
