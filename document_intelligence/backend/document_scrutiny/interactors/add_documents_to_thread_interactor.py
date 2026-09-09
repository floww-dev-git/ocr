from typing import List, Tuple

from document_scrutiny.adapters.document_file_store_interface import (
    DocumentFileStoreInterface,
)
from document_scrutiny.domain.upload_guard import UploadGuard
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.thread_dtos import (
    AddDocumentsRequestDTO,
    AddDocumentsToThreadDTO,
    IncomingFileDTO,
    StoredFileDTO,
    UploadLimitsDTO,
    WriteFileRequestDTO,
)
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class AddDocumentsToThreadInteractor:
    def __init__(
        self,
        thread_storage: ScrutinyThreadStorageInterface,
        document_file_store: DocumentFileStoreInterface,
        upload_limits: UploadLimitsDTO,
    ):
        self.thread_storage = thread_storage
        self.document_file_store = document_file_store
        self.upload_limits = upload_limits

    def add_documents(
        self, request: AddDocumentsRequestDTO
    ) -> List[DocumentStateDTO]:
        self.thread_storage.get_thread(thread_id=request.thread_id)
        if not request.incoming_files:
            return []

        for incoming in request.incoming_files:
            UploadGuard.check(incoming=incoming, limits=self.upload_limits)

        stored_files = self._store_files(
            thread_id=request.thread_id, incoming_files=request.incoming_files
        )
        return self.thread_storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=request.thread_id, stored_files=stored_files
            )
        )

    def _store_files(
        self, thread_id: str, incoming_files: Tuple[IncomingFileDTO, ...]
    ) -> Tuple[StoredFileDTO, ...]:
        return tuple(
            self._store_one_file(thread_id=thread_id, incoming=incoming)
            for incoming in incoming_files
        )

    def _store_one_file(
        self, thread_id: str, incoming: IncomingFileDTO
    ) -> StoredFileDTO:
        stored_path = self.document_file_store.write_file(
            write_file=WriteFileRequestDTO(
                thread_id=thread_id,
                stored_name=UploadGuard.build_stored_name(filename=incoming.filename),
                content=incoming.content,
            )
        )
        return StoredFileDTO(
            filename=incoming.filename,
            file_format=UploadGuard.read_file_format(filename=incoming.filename),
            file_size_bytes=len(incoming.content),
            stored_path=stored_path,
        )
