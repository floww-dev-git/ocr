import abc

from document_extraction.dtos.document_record_dtos import DocumentRecordDTO
from document_extraction.dtos.extraction_dtos import (
    DocumentClassificationDTO,
    ExtractDocumentRequestDTO,
)


class DocumentExtractorInterface(abc.ABC):
    @abc.abstractmethod
    def classify_document(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentClassificationDTO:
        pass

    @abc.abstractmethod
    def extract_document_record(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentRecordDTO:
        pass
