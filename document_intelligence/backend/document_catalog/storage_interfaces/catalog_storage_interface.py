import abc
from typing import List

from document_catalog.dtos.catalog_dtos import (
    DocumentTypeDTO,
    FilenameKeywordRuleDTO,
    IssuerServiceDTO,
)


class CatalogStorageInterface(abc.ABC):
    @abc.abstractmethod
    def get_document_types(self) -> List[DocumentTypeDTO]:
        pass

    @abc.abstractmethod
    def get_document_type(self, document_type_id: str) -> DocumentTypeDTO:
        pass

    @abc.abstractmethod
    def get_document_type_order(self) -> List[str]:
        pass

    @abc.abstractmethod
    def get_issuer_services(self) -> List[IssuerServiceDTO]:
        pass

    @abc.abstractmethod
    def get_issuer_service(self, issuer_service_id: str) -> IssuerServiceDTO:
        pass

    @abc.abstractmethod
    def get_filename_keyword_rules(self) -> List[FilenameKeywordRuleDTO]:
        pass
