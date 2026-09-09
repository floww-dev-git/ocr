import pytest

from document_catalog.exceptions.catalog_exceptions import ApplicationNotFound
from document_scrutiny.dtos.thread_dtos import (
    CreateScrutinyThreadDTO,
    ScrutinyThreadDTO,
)
from document_scrutiny.tests.conftest import CLEAN_APPLICATION_ID, ScrutinyStorageMock


class TestCreateScrutinyThreadInteractor(ScrutinyStorageMock):
    @pytest.fixture
    def interactor(self, thread_storage, catalog_service):
        from document_scrutiny.interactors.create_scrutiny_thread_interactor import (
            CreateScrutinyThreadInteractor,
        )

        return CreateScrutinyThreadInteractor(
            thread_storage=thread_storage, catalog_service=catalog_service
        )

    def test_a_thread_for_an_application_nobody_filed_raises_before_any_write(
        self, interactor, thread_storage
    ):
        # Arrange
        create_thread = CreateScrutinyThreadDTO(application_id="BN/2026/9999")

        # Act & Assert
        with pytest.raises(ApplicationNotFound):
            interactor.create_scrutiny_thread(create_thread=create_thread)
        thread_storage.create_thread.assert_not_called()

    def test_a_thread_is_opened_against_the_application_the_officer_picked(
        self, interactor, thread_storage
    ):
        # Arrange
        create_thread = CreateScrutinyThreadDTO(application_id=CLEAN_APPLICATION_ID)
        thread_storage.create_thread.return_value = ScrutinyThreadDTO(
            thread_id="thread_1", application_id=CLEAN_APPLICATION_ID
        )

        # Act
        thread = interactor.create_scrutiny_thread(create_thread=create_thread)

        # Assert
        thread_storage.create_thread.assert_called_once_with(create_thread=create_thread)
        assert thread.thread_id == "thread_1"
        assert thread.application_id == CLEAN_APPLICATION_ID
