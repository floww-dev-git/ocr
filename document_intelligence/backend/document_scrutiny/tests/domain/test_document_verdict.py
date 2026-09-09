import pytest

from document_scrutiny.constants.enums import (
    CheckStatus,
    DocumentStage,
    DocumentStatus,
)
from document_scrutiny.domain.document_verdict import DocumentVerdict
from document_scrutiny.tests.factories.scrutiny_dto_factories import CheckDTOFactory


class TestDocumentVerdict:
    @pytest.mark.parametrize(
        "stage",
        [
            DocumentStage.QUEUED.value,
            DocumentStage.IDENTIFYING.value,
            DocumentStage.EXTRACTING.value,
            DocumentStage.CHECKING.value,
            DocumentStage.VERIFYING.value,
        ],
    )
    def test_a_document_still_being_read_is_checking_whatever_its_checks_say(self, stage):
        # Arrange
        checks = (CheckDTOFactory(status=CheckStatus.FAIL.value),)

        # Act
        status = DocumentVerdict.derive(stage=stage, checks=checks)

        # Assert
        assert status == DocumentStatus.CHECKING.value

    def test_an_open_failure_outranks_an_open_warning(self):
        # Arrange
        checks = (
            CheckDTOFactory(status=CheckStatus.WARN.value),
            CheckDTOFactory(status=CheckStatus.FAIL.value),
        )

        # Act
        status = DocumentVerdict.derive(stage=DocumentStage.DONE.value, checks=checks)

        # Assert
        assert status == DocumentStatus.FAILED.value

    def test_an_open_unavailable_check_outranks_an_open_warning(self):
        # Arrange
        checks = (
            CheckDTOFactory(status=CheckStatus.WARN.value),
            CheckDTOFactory(status=CheckStatus.UNAVAILABLE.value),
        )

        # Act
        status = DocumentVerdict.derive(stage=DocumentStage.DONE.value, checks=checks)

        # Assert
        assert status == DocumentStatus.UNAVAILABLE.value

    def test_an_open_warning_needs_attention(self):
        # Arrange
        checks = (CheckDTOFactory(status=CheckStatus.WARN.value),)

        # Act
        status = DocumentVerdict.derive(stage=DocumentStage.DONE.value, checks=checks)

        # Assert
        assert status == DocumentStatus.ATTENTION.value

    def test_an_acknowledged_warning_stops_counting_as_open(self):
        # Arrange — AC9
        checks = (CheckDTOFactory(status=CheckStatus.WARN.value, acknowledged=True),)

        # Act
        status = DocumentVerdict.derive(stage=DocumentStage.DONE.value, checks=checks)

        # Assert
        assert status == DocumentStatus.VERIFIED.value

    def test_a_failure_marked_verified_by_hand_stops_counting_as_open(self):
        # Arrange
        checks = (CheckDTOFactory(status=CheckStatus.FAIL.value, manual=True),)

        # Act
        status = DocumentVerdict.derive(stage=DocumentStage.DONE.value, checks=checks)

        # Assert
        assert status == DocumentStatus.VERIFIED.value

    def test_requesting_a_document_from_the_applicant_does_not_close_the_finding(self):
        # Arrange — asking the applicant leaves the disagreement open
        checks = (CheckDTOFactory(status=CheckStatus.FAIL.value, requested=True),)

        # Act
        status = DocumentVerdict.derive(stage=DocumentStage.DONE.value, checks=checks)

        # Assert
        assert status == DocumentStatus.FAILED.value

    @pytest.mark.parametrize(
        "status", [CheckStatus.PASS.value, CheckStatus.INFO.value]
    )
    def test_passing_and_informational_checks_are_never_open(self, status):
        # Arrange
        checks = (CheckDTOFactory(status=status),)

        # Act
        document_status = DocumentVerdict.derive(
            stage=DocumentStage.DONE.value, checks=checks
        )

        # Assert
        assert document_status == DocumentStatus.VERIFIED.value

    def test_a_finished_document_with_no_checks_is_verified(self):
        # Act
        status = DocumentVerdict.derive(stage=DocumentStage.DONE.value, checks=())

        # Assert
        assert status == DocumentStatus.VERIFIED.value
