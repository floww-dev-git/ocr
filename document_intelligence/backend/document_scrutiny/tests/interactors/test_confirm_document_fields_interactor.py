import pytest

from document_scrutiny.dtos.officer_action_dtos import ConfirmDocumentFieldsRequestDTO
from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO
from document_scrutiny.tests.conftest import (
    MISMATCH_APPLICATION_ID,
    ScrutinyStorageMock,
    build_pan_field_values,
)
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    DocumentStateDTOFactory,
)

THREAD_ID = "thread_1"
DOCUMENT_ID = "document_1"


class TestConfirmDocumentFieldsInteractor(ScrutinyStorageMock):
    @pytest.fixture
    def interactor(self, thread_storage):
        from document_scrutiny.interactors.confirm_document_fields_interactor import (
            ConfirmDocumentFieldsInteractor,
        )

        return ConfirmDocumentFieldsInteractor(thread_storage=thread_storage)

    @pytest.fixture
    def document(self):
        return DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            confirmed=False,
            field_values=build_pan_field_values(
                name="MOHAMMED IRFAN SIDDIQUI",
                parent_name="MOHAMMED YOUSUF SIDDIQUI",
                date_of_birth="1982-11-27",
                pan="BNMPS7720K",
            ),
        )

    @pytest.fixture(autouse=True)
    def _arrange(self, thread_storage, document):
        thread_storage.get_document.return_value = document
        thread_storage.get_thread.return_value = ScrutinyThreadDTO(
            thread_id=THREAD_ID,
            application_id=MISMATCH_APPLICATION_ID,
            documents=(document,),
        )
        thread_storage.update_document.side_effect = (
            lambda update_document: update_document.document
        )

    def _confirm(self, interactor):
        return interactor.confirm_fields(
            request=ConfirmDocumentFieldsRequestDTO(
                thread_id=THREAD_ID, document_id=DOCUMENT_ID
            )
        )

    def test_signing_off_marks_the_document_confirmed(self, interactor):
        # Act
        change = self._confirm(interactor)

        # Assert
        assert change.document.confirmed is True

    def test_signing_off_covers_every_field_the_officer_reviewed(self, interactor):
        # Act
        change = self._confirm(interactor)

        # Assert
        assert all(value.confirmed for value in change.document.field_values)

    def test_signing_off_twice_leaves_the_same_result(self, interactor):
        # Act
        first = self._confirm(interactor)
        second = self._confirm(interactor)

        # Assert
        assert first.document == second.document

    def test_signing_off_does_not_disturb_the_read_values(self, interactor, document):
        # Act
        change = self._confirm(interactor)

        # Assert
        assert [value.value for value in change.document.field_values] == [
            value.value for value in document.field_values
        ]

    def test_the_confirmation_is_handed_to_storage(self, interactor, thread_storage):
        # Act
        self._confirm(interactor)

        # Assert
        update = thread_storage.update_document.call_args.kwargs["update_document"]
        assert update.thread_id == THREAD_ID
        assert update.document.confirmed is True
