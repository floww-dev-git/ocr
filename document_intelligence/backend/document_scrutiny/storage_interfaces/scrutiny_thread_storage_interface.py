import abc
from typing import List, Optional

from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.thread_dtos import (
    AddChildDocumentsDTO,
    AddDocumentsToThreadDTO,
    CreateScrutinyThreadDTO,
    DocumentLookupDTO,
    ScrutinyThreadDTO,
    UpdateDocumentDTO,
    UpdateServiceOverridesDTO,
)


class ScrutinyThreadStorageInterface(abc.ABC):
    @abc.abstractmethod
    def create_thread(
        self, create_thread: CreateScrutinyThreadDTO
    ) -> ScrutinyThreadDTO:
        pass

    @abc.abstractmethod
    def get_thread(self, thread_id: str) -> ScrutinyThreadDTO:
        pass

    @abc.abstractmethod
    def add_documents(
        self, add_documents: AddDocumentsToThreadDTO
    ) -> List[DocumentStateDTO]:
        pass

    @abc.abstractmethod
    def add_child_documents(
        self, add_children: AddChildDocumentsDTO
    ) -> List[DocumentStateDTO]:
        """Lists the documents found inside a bundled file, next to their parent.

        A child stores no file of its own. It is a page range of the parent's file,
        so `get_document_file_path` answers with the parent's path.
        """

    @abc.abstractmethod
    def get_document(self, lookup: DocumentLookupDTO) -> DocumentStateDTO:
        pass

    @abc.abstractmethod
    def get_document_file_path(self, lookup: DocumentLookupDTO) -> Optional[str]:
        pass

    @abc.abstractmethod
    def update_document(self, update_document: UpdateDocumentDTO) -> DocumentStateDTO:
        pass

    @abc.abstractmethod
    def update_service_overrides(
        self, update_overrides: UpdateServiceOverridesDTO
    ) -> ScrutinyThreadDTO:
        pass
