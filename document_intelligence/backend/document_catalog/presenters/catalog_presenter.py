from typing import Any, Dict, List

from document_catalog.dtos.catalog_dtos import (
    ApplicationDTO,
    ApplicationFieldSpecDTO,
    DocumentCatalogDTO,
    DocumentTypeDTO,
    FieldSpecDTO,
    IssuerServiceDTO,
    StructureSpecDTO,
)


class CatalogPresenter:
    def get_document_catalog_response(self, catalog: DocumentCatalogDTO) -> Dict[str, Any]:
        return {
            "documentTypes": [
                self._prep_document_type_response(document_type)
                for document_type in catalog.document_types
            ],
            "documentTypeOrder": list(catalog.document_type_order),
            "issuerServices": [
                self._prep_issuer_service_response(issuer_service)
                for issuer_service in catalog.issuer_services
            ],
            "applicationFieldSpecs": [
                self._prep_application_field_spec_response(field_spec)
                for field_spec in catalog.application_field_specs
            ],
        }

    def get_applications_response(
        self, applications: List[ApplicationDTO]
    ) -> Dict[str, Any]:
        return {
            "applications": [
                self._prep_application_response(application) for application in applications
            ]
        }

    @classmethod
    def _prep_document_type_response(cls, document_type: DocumentTypeDTO) -> Dict[str, Any]:
        return {
            "documentTypeId": document_type.document_type_id,
            "label": document_type.label,
            "icon": document_type.icon,
            "previewLayout": document_type.preview_layout,
            "issuerServiceId": document_type.issuer_service_id,
            "implemented": document_type.implemented,
            "fieldSpecs": [
                cls._prep_field_spec_response(field_spec)
                for field_spec in document_type.field_specs
            ],
            "structureSpecs": [
                cls._prep_structure_spec_response(structure_spec)
                for structure_spec in document_type.structure_specs
            ],
        }

    @staticmethod
    def _prep_field_spec_response(field_spec: FieldSpecDTO) -> Dict[str, Any]:
        return {
            "key": field_spec.key,
            "label": field_spec.label,
            "kind": field_spec.kind,
            "applicationFieldKey": field_spec.application_field_key,
            "masked": field_spec.masked,
            "comparisonRule": field_spec.comparison_rule,
        }

    @staticmethod
    def _prep_structure_spec_response(structure_spec: StructureSpecDTO) -> Dict[str, Any]:
        return {"key": structure_spec.key, "label": structure_spec.label}

    @staticmethod
    def _prep_issuer_service_response(issuer_service: IssuerServiceDTO) -> Dict[str, Any]:
        return {
            "issuerServiceId": issuer_service.issuer_service_id,
            "name": issuer_service.name,
            "latencyMs": issuer_service.latency_ms,
            "endpoint": issuer_service.endpoint,
        }

    @staticmethod
    def _prep_application_field_spec_response(
        field_spec: ApplicationFieldSpecDTO,
    ) -> Dict[str, Any]:
        return {
            "key": field_spec.key,
            "label": field_spec.label,
            "kind": field_spec.kind,
            "group": field_spec.group,
            "masked": field_spec.masked,
            "options": list(field_spec.options),
        }

    @staticmethod
    def _prep_application_response(application: ApplicationDTO) -> Dict[str, Any]:
        return {
            "applicationId": application.application_id,
            "status": application.status,
            "fieldValues": dict(application.field_values),
        }
