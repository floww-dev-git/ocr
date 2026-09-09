from document_catalog.app_interfaces.catalog_service_interface import (
    CatalogServiceInterface,
)
from document_scrutiny.dtos.thread_dtos import (
    CreateScrutinyThreadDTO,
    ScrutinyThreadDTO,
)
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class CreateScrutinyThreadInteractor:
    def __init__(
        self,
        thread_storage: ScrutinyThreadStorageInterface,
        catalog_service: CatalogServiceInterface,
    ):
        self.thread_storage = thread_storage
        self.catalog_service = catalog_service

    def create_scrutiny_thread(
        self, create_thread: CreateScrutinyThreadDTO
    ) -> ScrutinyThreadDTO:
        # The application is validated before anything is written, so a thread is
        # never created against an id the catalog does not know.
        self.catalog_service.get_application(
            application_id=create_thread.application_id
        )
        return self.thread_storage.create_thread(create_thread=create_thread)
