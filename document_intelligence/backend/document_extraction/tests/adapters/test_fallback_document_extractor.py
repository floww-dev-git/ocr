from unittest.mock import create_autospec

import pytest

from document_extraction.adapters.document_extractor_interface import (
    DocumentExtractorInterface,
)
from document_extraction.adapters.fallback_document_extractor import (
    FallbackDocumentExtractor,
)
from document_extraction.dtos.document_record_dtos import DocumentRecordDTO
from document_extraction.dtos.extraction_dtos import (
    DocumentClassificationDTO,
    ExtractDocumentRequestDTO,
)
from document_extraction.exceptions.extraction_exceptions import (
    DocumentReadNotRegistered,
    ExtractionCredentialMissing,
    ExtractionFailed,
)


def _request() -> ExtractDocumentRequestDTO:
    return ExtractDocumentRequestDTO(
        filename="aadhaar_clean.pdf",
        application_id="BN/2026/0601",
        source="upload",
        document_type_id="aadhaar",
    )


def _classification() -> DocumentClassificationDTO:
    return DocumentClassificationDTO(
        document_type_id="aadhaar",
        document_type_label="Aadhaar",
        type_confidence=0.98,
        implemented=True,
        page_count=2,
        total_page_count=2,
    )


class TestFallbackDocumentExtractor:
    @pytest.fixture
    def primary(self):
        return create_autospec(DocumentExtractorInterface)

    @pytest.fixture
    def fallback(self):
        return create_autospec(DocumentExtractorInterface)

    def test_the_primary_is_used_when_it_succeeds(self, primary, fallback):
        # Arrange
        primary.extract_document_record.return_value = DocumentRecordDTO()
        extractor = FallbackDocumentExtractor(primary=primary, fallback=fallback)

        # Act
        extractor.extract_document_record(request=_request())

        # Assert — the safety net is never touched when the primary works
        fallback.extract_document_record.assert_not_called()

    @pytest.mark.parametrize(
        "error",
        [
            ExtractionFailed(filename="aadhaar_clean.pdf", reason="network down"),
            ExtractionCredentialMissing(variable_name="GEMINI_API_KEY"),
        ],
    )
    def test_it_falls_back_when_the_primary_cannot_run(self, primary, fallback, error):
        # Arrange
        primary.extract_document_record.side_effect = error
        fallback.extract_document_record.return_value = DocumentRecordDTO()
        noted = []
        extractor = FallbackDocumentExtractor(
            primary=primary, fallback=fallback, on_fallback=lambda: noted.append(True)
        )

        # Act
        extractor.extract_document_record(request=_request())

        # Assert
        fallback.extract_document_record.assert_called_once()
        assert noted == [True]

    def test_classify_falls_back_too(self, primary, fallback):
        # Arrange
        primary.classify_document.side_effect = ExtractionFailed(
            filename="aadhaar_clean.pdf", reason="timeout"
        )
        fallback.classify_document.return_value = _classification()
        extractor = FallbackDocumentExtractor(primary=primary, fallback=fallback)

        # Act
        result = extractor.classify_document(request=_request())

        # Assert
        assert result.document_type_id == "aadhaar"
        fallback.classify_document.assert_called_once()

    def test_a_wiring_mistake_is_not_swallowed_by_the_fallback(self, primary, fallback):
        # Arrange — a missing read registration is a bug to surface, not to paper
        # over with the mock
        primary.extract_document_record.side_effect = DocumentReadNotRegistered(
            document_type_id="aadhaar"
        )
        extractor = FallbackDocumentExtractor(primary=primary, fallback=fallback)

        # Act & Assert
        with pytest.raises(DocumentReadNotRegistered):
            extractor.extract_document_record(request=_request())
        fallback.extract_document_record.assert_not_called()
