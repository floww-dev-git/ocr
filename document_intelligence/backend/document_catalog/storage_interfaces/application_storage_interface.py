import abc
from typing import List

from document_catalog.dtos.catalog_dtos import ApplicationDTO, ApplicationFieldSpecDTO


class ApplicationStorageInterface(abc.ABC):
    @abc.abstractmethod
    def get_applications(self) -> List[ApplicationDTO]:
        pass

    @abc.abstractmethod
    def get_application(self, application_id: str) -> ApplicationDTO:
        pass

    @abc.abstractmethod
    def get_application_field_specs(self) -> List[ApplicationFieldSpecDTO]:
        pass
