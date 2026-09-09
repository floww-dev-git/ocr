import pytest

from document_scrutiny.constants.enums import DocumentStage
from document_scrutiny.domain.officer_action_guard import OfficerActionGuard
from document_scrutiny.exceptions.scrutiny_exceptions import DocumentBusy
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    DocumentStateDTOFactory,
)

MID_RUN = (
    DocumentStage.IDENTIFYING.value,
    DocumentStage.EXTRACTING.value,
    DocumentStage.CHECKING.value,
    DocumentStage.VERIFYING.value,
)
SETTLED = (DocumentStage.QUEUED.value, DocumentStage.DONE.value)


class TestOfficerActionGuard:
    @pytest.mark.parametrize("stage", MID_RUN)
    def test_a_document_still_being_read_cannot_be_changed(self, stage):
        # Arrange
        document = DocumentStateDTOFactory(stage=stage)

        # Act & Assert
        with pytest.raises(DocumentBusy) as raised:
            OfficerActionGuard.check_document_is_not_being_read(document)

        assert raised.value.stage == stage
        assert raised.value.document_id == document.document_id

    @pytest.mark.parametrize("stage", SETTLED)
    def test_a_document_nobody_is_reading_can_be_changed(self, stage):
        # Arrange
        document = DocumentStateDTOFactory(stage=stage)

        # Act & Assert
        OfficerActionGuard.check_document_is_not_being_read(document)
