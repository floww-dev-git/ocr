from typing import List

from document_catalog.dtos.catalog_dtos import (
    ApplicationDTO,
    DocumentTypeDTO,
    FilenameKeywordRuleDTO,
    IssuerServiceDTO,
)
from document_catalog.storages.in_memory_application_storage import (
    InMemoryApplicationStorage,
)
from document_catalog.storages.in_memory_catalog_storage import InMemoryCatalogStorage


class CatalogServiceInterface:
    def __init__(self):
        self.catalog_storage = InMemoryCatalogStorage()
        self.application_storage = InMemoryApplicationStorage()

    def get_document_type(self, document_type_id: str) -> DocumentTypeDTO:
        return self.catalog_storage.get_document_type(document_type_id=document_type_id)

    def get_document_types(self) -> List[DocumentTypeDTO]:
        return self.catalog_storage.get_document_types()

    def get_filename_keyword_rules(self) -> List[FilenameKeywordRuleDTO]:
        return self.catalog_storage.get_filename_keyword_rules()

    def get_issuer_service(self, issuer_service_id: str) -> IssuerServiceDTO:
        return self.catalog_storage.get_issuer_service(issuer_service_id=issuer_service_id)

    def get_application(self, application_id: str) -> ApplicationDTO:
        return self.application_storage.get_application(application_id=application_id)
