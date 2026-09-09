import pytest
from django.test import override_settings

from document_extraction.adapters.extractor_factory import get_document_extractor
from document_extraction.adapters.mock_document_extractor import MockDocumentExtractor
from document_extraction.adapters.document_extractor_interface import DocumentExtractorInterface
from document_extraction.constants.extraction_constants import ExtractionMode
from document_extraction.exceptions.extraction_exceptions import (
    UnsupportedExtractionMode,
)


class TestGetDocumentExtractor:
    @override_settings(EXTRACTION_MODE="handwriting")
    def test_an_unrecognised_extraction_mode_raises_rather_than_falling_back(self):
        # Act & Assert
        with pytest.raises(UnsupportedExtractionMode) as exception_info:
            get_document_extractor()
        assert exception_info.value.extraction_mode == "handwriting"

    @override_settings(EXTRACTION_MODE=ExtractionMode.MOCK.value)
    def test_mock_mode_returns_the_mock_extractor(self):
        # Act
        extractor = get_document_extractor()

        # Assert
        assert isinstance(extractor, MockDocumentExtractor)

    @override_settings(EXTRACTION_MODE=ExtractionMode.MOCK.value)
    def test_every_extractor_honours_the_extractor_port(self):
        # Act
        extractor = get_document_extractor()

        # Assert
        assert isinstance(extractor, DocumentExtractorInterface)
