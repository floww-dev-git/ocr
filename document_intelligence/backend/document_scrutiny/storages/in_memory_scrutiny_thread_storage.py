import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from document_scrutiny.constants.enums import DocumentStage
from document_scrutiny.domain.document_verdict import DocumentVerdict
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.thread_dtos import (
    AddChildDocumentsDTO,
    AddDocumentsToThreadDTO,
    ChildDocumentDTO,
    CreateScrutinyThreadDTO,
    DocumentLookupDTO,
    ScrutinyThreadDTO,
    StoredFileDTO,
    UpdateDocumentDTO,
    UpdateServiceOverridesDTO,
)
from document_scrutiny.exceptions.scrutiny_exceptions import (
    DocumentNotFound,
    ScrutinyThreadNotFound,
)
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)

IDENTIFIER_LENGTH = 12
UNREAD_DOCUMENT_TYPE_LABEL = ""


@dataclass
class _ThreadRecord:
    thread_id: str
    application_id: str
    documents: List[DocumentStateDTO] = field(default_factory=list)
    stored_paths: Dict[str, str] = field(default_factory=dict)
    service_overrides: Dict[str, str] = field(default_factory=dict)


# Process-wide so every request sees the same threads; a database sits here later.
_THREAD_RECORDS: Dict[str, _ThreadRecord] = {}


def clear_scrutiny_threads() -> None:
    _THREAD_RECORDS.clear()


class InMemoryScrutinyThreadStorage(ScrutinyThreadStorageInterface):
    def create_thread(
        self, create_thread: CreateScrutinyThreadDTO
    ) -> ScrutinyThreadDTO:
        thread_id = f"thread_{uuid.uuid4().hex[:IDENTIFIER_LENGTH]}"
        record = _ThreadRecord(
            thread_id=thread_id, application_id=create_thread.application_id
        )
        _THREAD_RECORDS[thread_id] = record
        return self._prep_thread_dto(record)

    def get_thread(self, thread_id: str) -> ScrutinyThreadDTO:
        return self._prep_thread_dto(self._read_record(thread_id))

    def add_documents(
        self, add_documents: AddDocumentsToThreadDTO
    ) -> List[DocumentStateDTO]:
        record = self._read_record(add_documents.thread_id)
        added = []
        for stored_file in add_documents.stored_files:
            document = self._prep_queued_document_dto(stored_file)
            record.documents.append(document)
            record.stored_paths[document.document_id] = stored_file.stored_path
            added.append(document)
        return added

    def add_child_documents(
        self, add_children: AddChildDocumentsDTO
    ) -> List[DocumentStateDTO]:
        record = self._read_record(add_children.thread_id)
        parent_index = self._read_document_index(
            record=record, document_id=add_children.parent_document_id
        )
        added = [
            self._prep_child_document_dto(
                child=child, parent_document_id=add_children.parent_document_id
            )
            for child in add_children.children
        ]
        # Listed immediately after their parent, so the officer reads a bundle and
        # what came out of it together rather than at opposite ends of the thread.
        record.documents[parent_index + 1 : parent_index + 1] = added
        return added

    def get_document(self, lookup: DocumentLookupDTO) -> DocumentStateDTO:
        record = self._read_record(lookup.thread_id)
        for document in record.documents:
            if document.document_id == lookup.document_id:
                return document
        raise DocumentNotFound(
            thread_id=lookup.thread_id, document_id=lookup.document_id
        )

    def get_document_file_path(self, lookup: DocumentLookupDTO) -> Optional[str]:
        record = self._read_record(lookup.thread_id)
        stored_path = record.stored_paths.get(lookup.document_id)
        if stored_path is not None:
            return stored_path
        # A document carved out of a bundle has no file of its own; it is read from
        # its parent's, sliced to its own pages.
        parent_document_id = self._read_parent_document_id(
            record=record, document_id=lookup.document_id
        )
        if parent_document_id is None:
            return None
        return record.stored_paths.get(parent_document_id)

    def update_document(self, update_document: UpdateDocumentDTO) -> DocumentStateDTO:
        record = self._read_record(update_document.thread_id)
        replacement = update_document.document
        for index, document in enumerate(record.documents):
            if document.document_id == replacement.document_id:
                record.documents[index] = replacement
                return replacement
        raise DocumentNotFound(
            thread_id=update_document.thread_id,
            document_id=replacement.document_id,
        )

    def update_service_overrides(
        self, update_overrides: UpdateServiceOverridesDTO
    ) -> ScrutinyThreadDTO:
        record = self._read_record(update_overrides.thread_id)
        record.service_overrides = dict(update_overrides.service_overrides)
        return self._prep_thread_dto(record)

    @staticmethod
    def _read_record(thread_id: str) -> _ThreadRecord:
        record = _THREAD_RECORDS.get(thread_id)
        if record is None:
            raise ScrutinyThreadNotFound(thread_id=thread_id)
        return record

    @staticmethod
    def _read_document_index(record: _ThreadRecord, document_id: str) -> int:
        for index, document in enumerate(record.documents):
            if document.document_id == document_id:
                return index
        raise DocumentNotFound(
            thread_id=record.thread_id, document_id=document_id
        )

    @staticmethod
    def _read_parent_document_id(
        record: _ThreadRecord, document_id: str
    ) -> Optional[str]:
        for document in record.documents:
            if document.document_id == document_id:
                return document.parent_document_id
        return None

    @staticmethod
    def _prep_thread_dto(record: _ThreadRecord) -> ScrutinyThreadDTO:
        return ScrutinyThreadDTO(
            thread_id=record.thread_id,
            application_id=record.application_id,
            documents=tuple(record.documents),
            service_overrides=dict(record.service_overrides),
        )

    @staticmethod
    def _prep_queued_document_dto(stored_file: StoredFileDTO) -> DocumentStateDTO:
        stage = DocumentStage.QUEUED.value
        return DocumentStateDTO(
            document_id=f"document_{uuid.uuid4().hex[:IDENTIFIER_LENGTH]}",
            filename=stored_file.filename,
            file_format=stored_file.file_format,
            file_size_bytes=stored_file.file_size_bytes,
            document_type_id=None,
            document_type_label=UNREAD_DOCUMENT_TYPE_LABEL,
            type_confidence=0.0,
            implemented=False,
            stage=stage,
            status=DocumentVerdict.derive(stage=stage, checks=()),
            confirmed=False,
            page_count=0,
        )

    @staticmethod
    def _prep_child_document_dto(
        child: ChildDocumentDTO, parent_document_id: str
    ) -> DocumentStateDTO:
        stage = DocumentStage.QUEUED.value
        return DocumentStateDTO(
            document_id=f"document_{uuid.uuid4().hex[:IDENTIFIER_LENGTH]}",
            filename=child.filename,
            file_format=child.file_format,
            file_size_bytes=child.file_size_bytes,
            document_type_id=child.document_type_id,
            document_type_label=child.document_type_label,
            type_confidence=child.type_confidence,
            implemented=child.implemented,
            stage=stage,
            status=DocumentVerdict.derive(stage=stage, checks=()),
            confirmed=False,
            page_count=child.page_end - child.page_start + 1,
            parent_document_id=parent_document_id,
            page_start=child.page_start,
            page_end=child.page_end,
        )
