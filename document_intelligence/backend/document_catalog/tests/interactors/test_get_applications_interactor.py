import pytest

from document_catalog.tests.conftest import StorageMock
from document_catalog.tests.factories.catalog_dto_factories import ApplicationDTOFactory


class TestGetApplicationsInteractor(StorageMock):
    @pytest.fixture
    def interactor(self, application_storage):
        from document_catalog.interactors.get_applications_interactor import (
            GetApplicationsInteractor,
        )

        return GetApplicationsInteractor(application_storage=application_storage)

    def test_with_no_applications_returns_an_empty_list_without_raising(
        self, interactor, application_storage
    ):
        # Arrange
        application_storage.get_applications.return_value = []

        # Act
        applications = interactor.get_applications()

        # Assert
        assert applications == []

    def test_reads_the_application_storage_exactly_once(self, interactor, application_storage):
        # Arrange
        application_storage.get_applications.return_value = ApplicationDTOFactory.create_batch(
            size=3
        )

        # Act
        interactor.get_applications()

        # Assert
        application_storage.get_applications.assert_called_once_with()
        application_storage.get_application.assert_not_called()

    def test_returns_every_application_the_storage_reports(self, interactor, application_storage):
        # Arrange
        stored_applications = ApplicationDTOFactory.create_batch(size=3)
        application_storage.get_applications.return_value = stored_applications

        # Act
        applications = interactor.get_applications()

        # Assert
        assert applications == stored_applications
