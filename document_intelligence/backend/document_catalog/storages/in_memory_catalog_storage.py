from typing import Dict, List

from document_catalog.dtos.catalog_dtos import (
    DocumentTypeDTO,
    FilenameKeywordRuleDTO,
    IssuerServiceDTO,
)
from document_catalog.exceptions.catalog_exceptions import (
    DocumentTypeNotFound,
    IssuerServiceNotFound,
)
from document_catalog.storage_interfaces.catalog_storage_interface import (
    CatalogStorageInterface,
)
from document_catalog.storages.reference_data.document_type_specs import (
    DOCUMENT_TYPE_ORDER,
    DOCUMENT_TYPE_SPECS,
)
from document_catalog.storages.reference_data.filename_keyword_specs import (
    FILENAME_KEYWORD_RULES,
)
from document_catalog.storages.reference_data.issuer_service_specs import (
    ISSUER_SERVICE_SPECS,
)


class InMemoryCatalogStorage(CatalogStorageInterface):
    def get_document_types(self) -> List[DocumentTypeDTO]:
        return list(DOCUMENT_TYPE_SPECS)

    def get_document_type(self, document_type_id: str) -> DocumentTypeDTO:
        document_type = self._document_types_by_id().get(document_type_id)
        if document_type is None:
            raise DocumentTypeNotFound(document_type_id=document_type_id)
        return document_type

    def get_document_type_order(self) -> List[str]:
        return list(DOCUMENT_TYPE_ORDER)

    def get_issuer_services(self) -> List[IssuerServiceDTO]:
        return list(ISSUER_SERVICE_SPECS)

    def get_issuer_service(self, issuer_service_id: str) -> IssuerServiceDTO:
        issuer_service = self._issuer_services_by_id().get(issuer_service_id)
        if issuer_service is None:
            raise IssuerServiceNotFound(issuer_service_id=issuer_service_id)
        return issuer_service

    def get_filename_keyword_rules(self) -> List[FilenameKeywordRuleDTO]:
        return list(FILENAME_KEYWORD_RULES)

    @staticmethod
    def _document_types_by_id() -> Dict[str, DocumentTypeDTO]:
        return {
            document_type.document_type_id: document_type
            for document_type in DOCUMENT_TYPE_SPECS
        }

    @staticmethod
    def _issuer_services_by_id() -> Dict[str, IssuerServiceDTO]:
        return {
            issuer_service.issuer_service_id: issuer_service
            for issuer_service in ISSUER_SERVICE_SPECS
        }
