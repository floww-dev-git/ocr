from document_extraction.adapters.extractor_factory import get_document_extractor
from document_extraction.dtos.document_record_dtos import DocumentRecordDTO
from document_extraction.dtos.extraction_dtos import (
    DocumentClassificationDTO,
    ExtractDocumentRequestDTO,
)


class ExtractionServiceInterface:
    def classify_document(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentClassificationDTO:
        return get_document_extractor().classify_document(request=request)

    def extract_document_record(
        self, request: ExtractDocumentRequestDTO
    ) -> DocumentRecordDTO:
        return get_document_extractor().extract_document_record(request=request)
