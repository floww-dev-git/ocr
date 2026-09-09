from dataclasses import dataclass
from typing import Mapping, Tuple

from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.summary_dtos import ScrutinySummaryDTO


@dataclass(frozen=True)
class UpdateDocumentFieldRequestDTO:
    thread_id: str
    document_id: str
    field_key: str
    value: str


@dataclass(frozen=True)
class ConfirmDocumentFieldsRequestDTO:
    thread_id: str
    document_id: str


@dataclass(frozen=True)
class ResolveCheckRequestDTO:
    thread_id: str
    check_id: str
    action: str


@dataclass(frozen=True)
class RetryIssuerVerificationRequestDTO:
    thread_id: str
    document_id: str


@dataclass(frozen=True)
class UpdateServiceOverridesRequestDTO:
    thread_id: str
    service_overrides: Mapping[str, str]


@dataclass(frozen=True)
class DocumentChangeDTO:
    document: DocumentStateDTO
    summary: ScrutinySummaryDTO
    changed_check_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckChangeDTO:
    check: CheckDTO
    document: DocumentStateDTO
    summary: ScrutinySummaryDTO
