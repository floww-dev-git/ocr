from dataclasses import dataclass
from typing import Mapping, Optional, Tuple


@dataclass(frozen=True)
class FieldSpecDTO:
    key: str
    label: str
    kind: str
    application_field_key: Optional[str] = None
    masked: bool = False
    comparison_rule: Optional[str] = None


@dataclass(frozen=True)
class StructureSpecDTO:
    key: str
    label: str


@dataclass(frozen=True)
class DocumentTypeDTO:
    document_type_id: str
    label: str
    icon: str
    preview_layout: str
    issuer_service_id: Optional[str]
    implemented: bool
    field_specs: Tuple[FieldSpecDTO, ...]
    structure_specs: Tuple[StructureSpecDTO, ...]


@dataclass(frozen=True)
class IssuerServiceDTO:
    issuer_service_id: str
    name: str
    latency_ms: int
    endpoint: str


@dataclass(frozen=True)
class FilenameKeywordRuleDTO:
    keyword: str
    document_type_id: str


@dataclass(frozen=True)
class ApplicationFieldSpecDTO:
    key: str
    label: str
    kind: str
    group: str
    masked: bool = False
    options: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ApplicationDTO:
    application_id: str
    status: str
    field_values: Mapping[str, str]


@dataclass(frozen=True)
class DocumentCatalogDTO:
    document_types: Tuple[DocumentTypeDTO, ...]
    document_type_order: Tuple[str, ...]
    issuer_services: Tuple[IssuerServiceDTO, ...]
    application_field_specs: Tuple[ApplicationFieldSpecDTO, ...]
