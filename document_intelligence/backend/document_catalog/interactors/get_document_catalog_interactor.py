from document_catalog.dtos.catalog_dtos import DocumentCatalogDTO
from document_catalog.storage_interfaces.application_storage_interface import (
    ApplicationStorageInterface,
)
from document_catalog.storage_interfaces.catalog_storage_interface import (
    CatalogStorageInterface,
)


class GetDocumentCatalogInteractor:
    def __init__(
        self,
        catalog_storage: CatalogStorageInterface,
        application_storage: ApplicationStorageInterface,
    ):
        self.catalog_storage = catalog_storage
        self.application_storage = application_storage

    def get_document_catalog(self) -> DocumentCatalogDTO:
        return DocumentCatalogDTO(
            document_types=tuple(self.catalog_storage.get_document_types()),
            document_type_order=tuple(self.catalog_storage.get_document_type_order()),
            issuer_services=tuple(self.catalog_storage.get_issuer_services()),
            application_field_specs=tuple(
                self.application_storage.get_application_field_specs()
            ),
        )
