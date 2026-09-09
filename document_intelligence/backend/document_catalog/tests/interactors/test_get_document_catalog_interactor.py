import pytest

from document_catalog.tests.conftest import StorageMock
from document_catalog.tests.factories.catalog_dto_factories import (
    ApplicationFieldSpecDTOFactory,
    DocumentTypeDTOFactory,
    IssuerServiceDTOFactory,
)


class TestGetDocumentCatalogInteractor(StorageMock):
    @pytest.fixture
    def interactor(self, catalog_storage, application_storage):
        from document_catalog.interactors.get_document_catalog_interactor import (
            GetDocumentCatalogInteractor,
        )

        return GetDocumentCatalogInteractor(
            catalog_storage=catalog_storage,
            application_storage=application_storage,
        )

    def test_with_an_empty_catalog_returns_empty_collections_without_raising(
        self, interactor, catalog_storage, application_storage
    ):
        # Arrange
        catalog_storage.get_document_types.return_value = []
        catalog_storage.get_document_type_order.return_value = []
        catalog_storage.get_issuer_services.return_value = []
        application_storage.get_application_field_specs.return_value = []

        # Act
        catalog = interactor.get_document_catalog()

        # Assert
        assert catalog.document_types == ()
        assert catalog.document_type_order == ()
        assert catalog.issuer_services == ()
        assert catalog.application_field_specs == ()

    def test_reads_each_storage_collection_exactly_once(
        self, interactor, catalog_storage, application_storage
    ):
        # Arrange
        catalog_storage.get_document_types.return_value = DocumentTypeDTOFactory.create_batch(
            size=2
        )
        catalog_storage.get_document_type_order.return_value = ["document_type_1"]
        catalog_storage.get_issuer_services.return_value = (
            IssuerServiceDTOFactory.create_batch(size=1)
        )
        application_storage.get_application_field_specs.return_value = (
            ApplicationFieldSpecDTOFactory.create_batch(size=3)
        )

        # Act
        interactor.get_document_catalog()

        # Assert
        catalog_storage.get_document_types.assert_called_once_with()
        catalog_storage.get_document_type_order.assert_called_once_with()
        catalog_storage.get_issuer_services.assert_called_once_with()
        application_storage.get_application_field_specs.assert_called_once_with()
        catalog_storage.get_document_type.assert_not_called()

    def test_assembles_every_storage_collection_into_the_catalog(
        self, interactor, catalog_storage, application_storage
    ):
        # Arrange
        document_types = DocumentTypeDTOFactory.create_batch(size=2)
        issuer_services = IssuerServiceDTOFactory.create_batch(size=1)
        application_field_specs = ApplicationFieldSpecDTOFactory.create_batch(size=3)
        catalog_storage.get_document_types.return_value = document_types
        catalog_storage.get_document_type_order.return_value = ["document_type_2"]
        catalog_storage.get_issuer_services.return_value = issuer_services
        application_storage.get_application_field_specs.return_value = application_field_specs

        # Act
        catalog = interactor.get_document_catalog()

        # Assert
        assert catalog.document_types == tuple(document_types)
        assert catalog.document_type_order == ("document_type_2",)
        assert catalog.issuer_services == tuple(issuer_services)
        assert catalog.application_field_specs == tuple(application_field_specs)
