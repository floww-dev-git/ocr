from pathlib import Path

from django.conf import settings

from document_scrutiny.adapters.document_file_store_interface import (
    DocumentFileStoreInterface,
)
from document_scrutiny.dtos.thread_dtos import WriteFileRequestDTO


class LocalDocumentFileStore(DocumentFileStoreInterface):
    def write_file(self, write_file: WriteFileRequestDTO) -> str:
        thread_directory = Path(settings.UPLOADS_ROOT) / write_file.thread_id
        thread_directory.mkdir(parents=True, exist_ok=True)
        stored_path = thread_directory / write_file.stored_name
        stored_path.write_bytes(write_file.content)
        return str(stored_path)
