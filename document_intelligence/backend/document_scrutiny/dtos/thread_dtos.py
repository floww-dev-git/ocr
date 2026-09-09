from dataclasses import dataclass, field
from typing import Mapping, Tuple

from document_scrutiny.dtos.document_dtos import DocumentStateDTO


@dataclass(frozen=True)
class ScrutinyThreadDTO:
    thread_id: str
    application_id: str
    documents: Tuple[DocumentStateDTO, ...] = ()
    service_overrides: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CreateScrutinyThreadDTO:
    application_id: str


@dataclass(frozen=True)
class IncomingFileDTO:
    filename: str
    content: bytes


@dataclass(frozen=True)
class UploadLimitsDTO:
    allowed_extensions: Tuple[str, ...]
    max_bytes: int


@dataclass(frozen=True)
class StoredFileDTO:
    filename: str
    file_format: str
    file_size_bytes: int
    stored_path: str


@dataclass(frozen=True)
class AddDocumentsToThreadDTO:
    thread_id: str
    stored_files: Tuple[StoredFileDTO, ...]


@dataclass(frozen=True)
class AddDocumentsRequestDTO:
    thread_id: str
    incoming_files: Tuple[IncomingFileDTO, ...]


@dataclass(frozen=True)
class ChildDocumentDTO:
    """One document found inside a bundled file, ready to be listed in its own right.

    It arrives already identified, because the pass that found it inside the file
    is the one that could tell what it was — a slice read on its own cannot know
    whether it is the deed being relied on or one of the deeds behind it.
    """

    filename: str
    file_format: str
    file_size_bytes: int
    document_type_id: str
    document_type_label: str
    type_confidence: float
    implemented: bool
    page_start: int
    page_end: int


@dataclass(frozen=True)
class AddChildDocumentsDTO:
    thread_id: str
    parent_document_id: str
    children: Tuple[ChildDocumentDTO, ...]


@dataclass(frozen=True)
class DocumentLookupDTO:
    thread_id: str
    document_id: str


@dataclass(frozen=True)
class UpdateDocumentDTO:
    thread_id: str
    document: DocumentStateDTO


@dataclass(frozen=True)
class UpdateServiceOverridesDTO:
    thread_id: str
    service_overrides: Mapping[str, str]


@dataclass(frozen=True)
class WriteFileRequestDTO:
    thread_id: str
    stored_name: str
    content: bytes

