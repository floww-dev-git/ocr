import dataclasses

import pytest

from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.adapters.reads.field_read_mapper import FieldReadMapper
from document_extraction.adapters.reads.pan_card_read import PAN_CARD_READ, PanCardRead
from document_extraction.constants.extraction_constants import (
    LOW_CONFIDENCE_THRESHOLD,
    UNCERTAIN_FIELD_CONFIDENCE,
    DocumentSource,
)
from document_extraction.dtos.document_record_dtos import DocumentRecordDTO


def build_model_read(**overrides) -> PanCardRead:
    defaults = {
        "name": "SRINIVAS RAO KANDULA",
        "parent_name": "VENKATESWARA RAO KANDULA",
        "date_of_birth": "1979-08-14",
        "pan": "DQRPK4831L",
        "photograph_present": True,
        "signature_present": True,
        "hologram_present": True,
        "confidence": 0.94,
        "low_confidence_fields": [],
        "boxes": [
            FieldBoxRead(
                label="name", value="SRINIVAS RAO KANDULA", page=0, box=[222, 386, 268, 792]
            ),
            FieldBoxRead(label="pan", value="DQRPK4831L", page=0, box=[446, 386, 498, 704]),
        ],
    }
    defaults.update(overrides)
    return PanCardRead(**defaults)


class TestFieldReadMapper:
    def test_a_read_with_every_field_missing_yields_no_field_reads(self):
        # Arrange
        model_read = build_model_read(
            name=None, parent_name=None, date_of_birth=None, pan=None, boxes=[]
        )

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.UPLOAD.value, page_count=1
        )

        # Assert
        assert record.field_reads == ()
        assert record.overall_confidence == 0.0

    def test_a_field_read_as_blank_is_dropped_rather_than_carried_as_empty(self):
        # Arrange
        model_read = build_model_read(parent_name="   ")

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.SAMPLE.value, page_count=1
        )

        # Assert
        assert "parentName" not in {read.key for read in record.field_reads}

    def test_a_box_with_the_wrong_coordinate_count_is_discarded(self):
        # Arrange
        model_read = build_model_read(
            boxes=[
                FieldBoxRead(label="name", value="X", page=0, box=[1, 2, 3]),
                FieldBoxRead(label="pan", value="Y", page=0, box=[]),
            ]
        )

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.SAMPLE.value, page_count=1
        )

        # Assert
        assert record.boxes == ()

    def test_a_box_coordinate_outside_the_scale_is_clamped(self):
        # Arrange
        model_read = build_model_read(
            boxes=[
                FieldBoxRead(label="name", value="X", page=0, box=[-40, 386, 268, 4000]),
            ]
        )

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.SAMPLE.value, page_count=1
        )

        # Assert
        assert record.boxes[0].box == (0, 386, 268, 1000)

    def test_a_box_naming_a_field_the_card_does_not_have_is_discarded(self):
        # Arrange
        model_read = build_model_read(
            boxes=[FieldBoxRead(label="aadhaarNo", value="X", page=0, box=[1, 2, 3, 4])]
        )

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.SAMPLE.value, page_count=1
        )

        # Assert
        assert record.boxes == ()

    def test_the_model_field_names_are_mapped_onto_the_catalog_field_keys(self):
        # Arrange
        model_read = build_model_read()

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.SAMPLE.value, page_count=1
        )

        # Assert
        assert {read.key: read.value for read in record.field_reads} == {
            "name": "SRINIVAS RAO KANDULA",
            "parentName": "VENKATESWARA RAO KANDULA",
            "dob": "1979-08-14",
            "pan": "DQRPK4831L",
        }

    def test_the_structure_booleans_are_mapped_onto_the_catalog_structure_keys(self):
        # Arrange
        model_read = build_model_read(hologram_present=False)

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.SAMPLE.value, page_count=1
        )

        # Assert
        assert record.structure_findings == {
            "photo": True,
            "signature": True,
            "hologram": False,
        }

    def test_a_field_the_model_doubted_lands_below_the_review_threshold(self):
        # Arrange
        model_read = build_model_read(low_confidence_fields=["parentName"])

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.SAMPLE.value, page_count=1
        )

        # Assert
        confidences = {read.key: read.confidence for read in record.field_reads}
        assert confidences["parentName"] == UNCERTAIN_FIELD_CONFIDENCE
        assert confidences["name"] == 0.94
        assert record.low_confidence_fields == ("parentName",)
        assert confidences["parentName"] < LOW_CONFIDENCE_THRESHOLD

    def test_the_model_doubt_list_is_matched_by_catalog_key_or_model_attribute_name(self):
        # Arrange — the model may echo either spelling back
        model_read = build_model_read(low_confidence_fields=["parent_name", "date_of_birth"])

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.SAMPLE.value, page_count=1
        )

        # Assert
        assert set(record.low_confidence_fields) == {"parentName", "dob"}

    def test_an_uploaded_read_is_discounted_like_every_other_source(self):
        # Arrange
        model_read = build_model_read()

        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=model_read, source=DocumentSource.UPLOAD.value, page_count=1
        )

        # Assert
        assert {read.confidence for read in record.field_reads} == {0.8}

    def test_the_mapped_record_has_the_same_shape_the_mock_extractor_produces(self):
        # Arrange — one DocumentRecordDTO contract, whichever adapter filled it
        from document_extraction.adapters.mock_document_extractor import MockDocumentExtractor
        from document_extraction.dtos.extraction_dtos import ExtractDocumentRequestDTO

        mock_record = MockDocumentExtractor().extract_document_record(
            request=ExtractDocumentRequestDTO(
                filename="pan_card.pdf",
                application_id="BN/2026/0421",
                source=DocumentSource.SAMPLE.value,
                document_type_id="pan",
            )
        )

        # Act
        gemini_record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=build_model_read(), source=DocumentSource.SAMPLE.value, page_count=1
        )

        # Assert
        assert isinstance(gemini_record, DocumentRecordDTO)
        assert {field.name for field in dataclasses.fields(gemini_record)} == {
            field.name for field in dataclasses.fields(mock_record)
        }
        assert {read.key for read in gemini_record.field_reads} == {
            read.key for read in mock_record.field_reads
        }
        assert set(gemini_record.structure_findings) == set(mock_record.structure_findings)
        assert {box.field_key for box in gemini_record.boxes} <= {
            box.field_key for box in mock_record.boxes
        }

    @pytest.mark.parametrize("reported_page_count", [1, 2])
    def test_the_page_count_is_carried_from_the_rendered_pages(self, reported_page_count):
        # Act
        record = FieldReadMapper.to_document_record(
            read_spec=PAN_CARD_READ,
            model_read=build_model_read(),
            source=DocumentSource.SAMPLE.value,
            page_count=reported_page_count,
        )

        # Assert
        assert record.page_count == reported_page_count
