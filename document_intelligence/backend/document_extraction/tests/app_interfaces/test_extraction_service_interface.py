import pytest

from document_extraction.constants.extraction_constants import (
    DocumentSource,
    ExtractionMode,
)
from document_extraction.dtos.extraction_dtos import ExtractDocumentRequestDTO
from document_extraction.exceptions.extraction_exceptions import (
    NoSampleReadForApplication,
)

CLEAN_APPLICATION_ID = "BN/2026/0421"


class TestExtractionServiceInterface:
    @pytest.fixture(autouse=True)
    def mock_extraction_mode(self, settings):
        settings.EXTRACTION_MODE = ExtractionMode.MOCK.value

    @pytest.fixture
    def service_interface(self):
        from document_extraction.app_interfaces.extraction_service_interface import (
            ExtractionServiceInterface,
        )

        return ExtractionServiceInterface()

    @pytest.fixture
    def request_dto(self):
        return ExtractDocumentRequestDTO(
            filename="pan_card.pdf",
            application_id=CLEAN_APPLICATION_ID,
            source=DocumentSource.SAMPLE.value,
            document_type_id="pan",
        )

    def test_an_application_with_no_sample_read_propagates_the_domain_exception(
        self, service_interface
    ):
        # Arrange
        request = ExtractDocumentRequestDTO(
            filename="pan_card.pdf",
            application_id="BN/2026/9999",
            source=DocumentSource.SAMPLE.value,
            document_type_id="pan",
        )

        # Act & Assert
        with pytest.raises(NoSampleReadForApplication):
            service_interface.extract_document_record(request=request)

    def test_exposes_classification_to_consuming_apps(
        self, service_interface, request_dto
    ):
        # Act
        classification = service_interface.classify_document(request=request_dto)

        # Assert
        assert classification.document_type_id == "pan"
        assert classification.implemented is True

    def test_exposes_the_document_record_to_consuming_apps(
        self, service_interface, request_dto
    ):
        # Act
        record = service_interface.extract_document_record(request=request_dto)

        # Assert
        assert len(record.field_reads) == 4
        assert len(record.boxes) == 4
        assert record.structure_findings["hologram"] is True
