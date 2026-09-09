import pytest

from document_extraction.constants.extraction_constants import (
    LOW_CONFIDENCE_THRESHOLD,
    DocumentSource,
)
from document_extraction.domain.read_confidence import ReadConfidence
from document_extraction.dtos.document_record_dtos import FieldReadDTO


class TestReadConfidence:
    def test_a_sample_read_keeps_its_confidence(self):
        # Arrange
        source = DocumentSource.SAMPLE.value

        # Act
        confidence = ReadConfidence.for_source(confidence=0.98, source=source)

        # Assert
        assert confidence == 0.98

    def test_an_uploaded_read_is_discounted_because_the_file_is_unseen(self):
        # Arrange — the prototype applies a 0.85 factor to upload-sourced reads
        source = DocumentSource.UPLOAD.value

        # Act
        confidence = ReadConfidence.for_source(confidence=0.98, source=source)

        # Assert
        assert confidence == 0.83

    def test_the_discounted_confidence_rounds_half_up_to_two_places(self):
        # Arrange — 0.95 * 0.85 is 0.8075, which must land on 0.81
        # Act
        confidence = ReadConfidence.for_source(
            confidence=0.95, source=DocumentSource.UPLOAD.value
        )

        # Assert
        assert confidence == 0.81

    @pytest.mark.parametrize("confidence", [0.0, 1.0])
    def test_the_confidence_bounds_survive_the_mapping(self, confidence):
        # Act
        sample_confidence = ReadConfidence.for_source(
            confidence=confidence, source=DocumentSource.SAMPLE.value
        )

        # Assert
        assert sample_confidence == confidence

    def test_no_field_is_low_confidence_when_every_read_is_certain(self):
        # Arrange
        field_reads = (
            FieldReadDTO(key="name", value="A", confidence=0.98),
            FieldReadDTO(key="pan", value="B", confidence=0.99),
        )

        # Act
        low_confidence_fields = ReadConfidence.collect_low_confidence_field_keys(
            field_reads=field_reads
        )

        # Assert
        assert low_confidence_fields == ()

    def test_a_field_below_the_review_threshold_is_reported_for_review(self):
        # Arrange
        field_reads = (
            FieldReadDTO(key="name", value="A", confidence=0.98),
            FieldReadDTO(key="parentName", value="B", confidence=0.61),
            FieldReadDTO(key="pan", value="C", confidence=0.4),
        )

        # Act
        low_confidence_fields = ReadConfidence.collect_low_confidence_field_keys(
            field_reads=field_reads
        )

        # Assert
        assert low_confidence_fields == ("parentName", "pan")

    def test_a_field_exactly_on_the_threshold_is_not_low_confidence(self):
        # Arrange
        field_reads = (
            FieldReadDTO(key="name", value="A", confidence=LOW_CONFIDENCE_THRESHOLD),
        )

        # Act
        low_confidence_fields = ReadConfidence.collect_low_confidence_field_keys(
            field_reads=field_reads
        )

        # Assert
        assert low_confidence_fields == ()

    def test_every_reported_low_confidence_field_is_genuinely_below_the_threshold(self):
        # Arrange
        field_reads = (
            FieldReadDTO(key="name", value="A", confidence=0.79),
            FieldReadDTO(key="parentName", value="B", confidence=0.8),
            FieldReadDTO(key="dob", value="C", confidence=0.81),
        )
        confidences_by_key = {read.key: read.confidence for read in field_reads}

        # Act
        low_confidence_fields = ReadConfidence.collect_low_confidence_field_keys(
            field_reads=field_reads
        )

        # Assert
        assert all(
            confidences_by_key[key] < LOW_CONFIDENCE_THRESHOLD
            for key in low_confidence_fields
        )

    def test_the_overall_confidence_of_no_reads_is_zero(self):
        # Act
        overall = ReadConfidence.overall(field_reads=())

        # Assert
        assert overall == 0.0

    def test_the_overall_confidence_is_the_weakest_field_read(self):
        # Arrange — a record is only as trustworthy as its shakiest field
        field_reads = (
            FieldReadDTO(key="name", value="A", confidence=0.98),
            FieldReadDTO(key="parentName", value="B", confidence=0.95),
            FieldReadDTO(key="pan", value="C", confidence=0.99),
        )

        # Act
        overall = ReadConfidence.overall(field_reads=field_reads)

        # Assert
        assert overall == 0.95
