from typing import List

from document_catalog.dtos.catalog_dtos import ApplicationDTO
from document_catalog.storage_interfaces.application_storage_interface import (
    ApplicationStorageInterface,
)


class GetApplicationsInteractor:
    def __init__(self, application_storage: ApplicationStorageInterface):
        self.application_storage = application_storage

    def get_applications(self) -> List[ApplicationDTO]:
        return self.application_storage.get_applications()
