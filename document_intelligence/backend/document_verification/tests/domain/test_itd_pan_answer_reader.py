import pytest

from document_verification.constants.verification_constants import (
    DisagreeingField,
    IssuerOutcome,
    IssuerStatus,
)
from document_verification.domain.itd_pan_answer_reader import ItdPanAnswerReader


class TestItdPanAnswerReader:
    def test_an_answer_with_no_status_cannot_be_read(self):
        # Arrange
        body = {"referenceId": "ITD/ABC"}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome is None
        assert disagreeing == ()

    def test_an_answer_with_a_status_nobody_declared_cannot_be_read(self):
        # Arrange
        body = {"status": "MAYBE"}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome is None

    def test_a_pan_the_department_does_not_hold_is_no_record(self):
        # Arrange
        body = {"status": IssuerStatus.NOT_FOUND.value, "nameMatch": None, "dobMatch": None}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome == IssuerOutcome.NO_RECORD.value
        assert disagreeing == ()

    def test_a_demographic_rejection_is_not_matched(self):
        # Arrange
        body = {"status": IssuerStatus.NOT_MATCHED.value, "nameMatch": None, "dobMatch": None}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome == IssuerOutcome.NOT_MATCHED.value

    def test_a_disagreeing_name_is_a_partial_match_naming_the_field(self):
        # Arrange — AC6: the verdict must follow the payload it discloses
        body = {"status": IssuerStatus.VALID.value, "nameMatch": False, "dobMatch": True}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert disagreeing == (DisagreeingField.NAME.value,)

    def test_a_disagreeing_date_of_birth_is_also_a_partial_match(self):
        # Arrange
        body = {"status": IssuerStatus.VALID.value, "nameMatch": True, "dobMatch": False}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert disagreeing == (DisagreeingField.DATE_OF_BIRTH.value,)

    def test_both_demographics_disagreeing_are_both_named(self):
        # Arrange
        body = {"status": IssuerStatus.VALID.value, "nameMatch": False, "dobMatch": False}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert disagreeing == (
            DisagreeingField.NAME.value,
            DisagreeingField.DATE_OF_BIRTH.value,
        )

    def test_a_date_of_birth_that_was_never_asked_about_does_not_disagree(self):
        # Arrange — null means not asked, and must never read as a mismatch
        body = {"status": IssuerStatus.VALID.value, "nameMatch": True, "dobMatch": None}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome == IssuerOutcome.CONFIRMED.value
        assert disagreeing == ()

    def test_a_full_agreement_is_confirmed(self):
        # Arrange — AC1
        body = {"status": IssuerStatus.VALID.value, "nameMatch": True, "dobMatch": True}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome == IssuerOutcome.CONFIRMED.value
        assert disagreeing == ()

    @pytest.mark.parametrize("name_match", [None, "yes", 0])
    def test_a_name_match_that_is_not_a_boolean_is_treated_as_not_agreeing(
        self, name_match
    ):
        # Arrange — only an explicit true confirms the name
        body = {"status": IssuerStatus.VALID.value, "nameMatch": name_match}

        # Act
        outcome, disagreeing = ItdPanAnswerReader.read(body=body)

        # Assert
        assert outcome == IssuerOutcome.PARTIAL_MATCH.value
        assert DisagreeingField.NAME.value in disagreeing
