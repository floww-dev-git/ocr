import abc

from document_scrutiny.dtos.thread_dtos import WriteFileRequestDTO


class DocumentFileStoreInterface(abc.ABC):
    @abc.abstractmethod
    def write_file(self, write_file: WriteFileRequestDTO) -> str:
        pass
