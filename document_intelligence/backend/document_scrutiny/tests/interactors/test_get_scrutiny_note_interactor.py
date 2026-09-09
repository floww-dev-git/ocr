import pytest

from document_scrutiny.constants.enums import CheckGroup, CheckStatus, DocumentStage
from document_scrutiny.domain.scrutiny_note import (
    FIT_TO_PROCEED_RECOMMENDATION,
    RAISE_SHORTFALL_RECOMMENDATION,
)
from document_scrutiny.dtos.note_dtos import ScrutinyNoteRequestDTO
from document_scrutiny.tests.conftest import (
    MISMATCH_APPLICATION_ID,
    ScrutinyStorageMock,
    wire_document_memory,
)
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    CheckDTOFactory,
    DocumentStateDTOFactory,
)

THREAD_ID = "thread_1"
DOCUMENT_ID = "document_1"


class TestGetScrutinyNoteInteractor(ScrutinyStorageMock):
    @pytest.fixture
    def interactor(self, thread_storage, catalog_service):
        from document_scrutiny.interactors.get_scrutiny_note_interactor import (
            GetScrutinyNoteInteractor,
        )

        return GetScrutinyNoteInteractor(
            thread_storage=thread_storage, catalog_service=catalog_service
        )

    def _arrange(self, thread_storage, checks=()):
        wire_document_memory(
            thread_storage=thread_storage,
            documents=(
                DocumentStateDTOFactory(
                    document_id=DOCUMENT_ID,
                    document_type_label="PAN",
                    stage=DocumentStage.DONE.value,
                    checks=checks,
                ),
            ),
            application_id=MISMATCH_APPLICATION_ID,
        )

    def _note(self, interactor):
        return interactor.get_note(
            request=ScrutinyNoteRequestDTO(thread_id=THREAD_ID)
        )

    def test_the_note_names_the_application_it_was_written_for(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(thread_storage)

        # Act
        note = self._note(interactor)

        # Assert
        assert note.thread_id == THREAD_ID
        assert MISMATCH_APPLICATION_ID in note.text

    def test_the_note_reads_the_application_details_from_the_record(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(thread_storage)

        # Act
        note = self._note(interactor)

        # Assert
        assert "Mohammed Irfan Siddiqui" in note.text
        assert "Kokapet" in note.text

    def test_a_thread_with_an_open_warning_is_not_recommended_for_sanction(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(
            thread_storage,
            checks=(
                CheckDTOFactory(
                    check_id=f"{DOCUMENT_ID}:issuer",
                    document_id=DOCUMENT_ID,
                    group=CheckGroup.EXTERNAL.value,
                    status=CheckStatus.WARN.value,
                    title="Income Tax PAN verification did not fully match",
                    detail="The department holds this PAN but its record does not agree on the name.",
                ),
            ),
        )

        # Act
        note = self._note(interactor)

        # Assert
        assert RAISE_SHORTFALL_RECOMMENDATION in note.text
        assert "Open: PAN: Income Tax PAN verification did not fully match" in note.text
        assert "does not agree on the name" in note.text

    def test_a_thread_with_everything_settled_is_fit_to_proceed(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(
            thread_storage,
            checks=(
                CheckDTOFactory(
                    check_id=f"{DOCUMENT_ID}:name",
                    document_id=DOCUMENT_ID,
                    status=CheckStatus.PASS.value,
                ),
            ),
        )

        # Act
        note = self._note(interactor)

        # Assert
        assert FIT_TO_PROCEED_RECOMMENDATION in note.text
        assert "Checks: 1 passed, 0 warnings, 0 failed, 0 unavailable" in note.text

    def test_a_warning_the_officer_settled_no_longer_holds_the_note_open(
        self, interactor, thread_storage
    ):
        # Arrange
        self._arrange(
            thread_storage,
            checks=(
                CheckDTOFactory(
                    check_id=f"{DOCUMENT_ID}:issuer",
                    document_id=DOCUMENT_ID,
                    group=CheckGroup.EXTERNAL.value,
                    status=CheckStatus.WARN.value,
                    manual=True,
                ),
            ),
        )

        # Act
        note = self._note(interactor)

        # Assert
        assert FIT_TO_PROCEED_RECOMMENDATION in note.text
        assert "Open:" not in note.text
