from unittest.mock import patch

import pytest

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import DocumentIdentification
from document_extraction.adapters.reads.pan_card_read import PanCardRead
from document_extraction.constants.extraction_constants import (
    GEMINI_API_KEY_VARIABLE,
    DocumentSource,
)
from document_extraction.dtos.extraction_dtos import ExtractDocumentRequestDTO
from document_extraction.exceptions.extraction_exceptions import (
    DocumentReadNotRegistered,
    ExtractionCredentialMissing,
    ExtractionFailed,
)

PAN = DocumentTypeEnum.PAN.value

GENERATE_PARSED = "document_extraction.adapters.gemini_document_extractor.generate_parsed"
RENDER_PAGE_IMAGES = "document_extraction.adapters.gemini_document_extractor.render_page_images"
BUILD_IMAGE_PARTS = "document_extraction.adapters.gemini_document_extractor.build_image_parts"
BUILD_TEXT_PART = "document_extraction.adapters.gemini_document_extractor.build_text_part"
DOWNSCALE_PNG = "document_extraction.adapters.gemini_document_extractor.downscale_png"


@pytest.fixture
def extractor():
    from document_extraction.adapters.gemini_document_extractor import GeminiDocumentExtractor

    return GeminiDocumentExtractor()


@pytest.fixture
def request_dto(tmp_path):
    stored_file = tmp_path / "pan_card.png"
    stored_file.write_bytes(b"not-a-real-image")
    return ExtractDocumentRequestDTO(
        filename="pan_card.png",
        application_id="BN/2026/0421",
        source=DocumentSource.UPLOAD.value,
        file_path=str(stored_file),
        document_type_id=PAN,
    )


@pytest.fixture(autouse=True)
def stubbed_model_parts():
    with patch(BUILD_IMAGE_PARTS, return_value=[]), patch(
        BUILD_TEXT_PART, return_value="prompt"
    ), patch(DOWNSCALE_PNG, side_effect=lambda page: page):
        yield


class TestGeminiDocumentExtractorFailurePaths:
    def test_a_request_with_no_stored_file_fails_before_any_model_call(
        self, extractor, request_dto
    ):
        # Arrange
        request = ExtractDocumentRequestDTO(
            filename=request_dto.filename,
            application_id=request_dto.application_id,
            source=request_dto.source,
            file_path=None,
            document_type_id=PAN,
        )

        # Act & Assert
        with patch(GENERATE_PARSED) as generate:
            with pytest.raises(ExtractionFailed) as exception_info:
                extractor.extract_document_record(request=request)
        generate.assert_not_called()
        assert exception_info.value.filename == "pan_card.png"
        assert "stored file" in exception_info.value.reason

    def test_a_missing_file_on_disk_fails_before_any_model_call(self, extractor, tmp_path):
        # Arrange
        request = ExtractDocumentRequestDTO(
            filename="gone.png",
            application_id="BN/2026/0421",
            source=DocumentSource.UPLOAD.value,
            file_path=str(tmp_path / "gone.png"),
            document_type_id=PAN,
        )

        # Act & Assert
        with patch(GENERATE_PARSED) as generate:
            with pytest.raises(ExtractionFailed):
                extractor.extract_document_record(request=request)
        generate.assert_not_called()

    def test_an_unreadable_file_format_fails_before_any_model_call(
        self, extractor, tmp_path
    ):
        # Arrange
        stored_file = tmp_path / "notes.txt"
        stored_file.write_text("plain text")
        request = ExtractDocumentRequestDTO(
            filename="notes.txt",
            application_id="BN/2026/0421",
            source=DocumentSource.UPLOAD.value,
            file_path=str(stored_file),
            document_type_id=PAN,
        )

        # Act & Assert
        with patch(GENERATE_PARSED) as generate:
            with pytest.raises(ExtractionFailed) as exception_info:
                extractor.extract_document_record(request=request)
        generate.assert_not_called()
        assert "readable document format" in exception_info.value.reason

    def test_a_model_timeout_is_translated_and_keeps_its_cause(self, extractor, request_dto):
        # Arrange
        timeout = TimeoutError("deadline exceeded")

        # Act & Assert
        with patch(RENDER_PAGE_IMAGES, return_value=([b"page"], 1)):
            with patch(GENERATE_PARSED, side_effect=timeout):
                with pytest.raises(ExtractionFailed) as exception_info:
                    extractor.extract_document_record(request=request_dto)
        assert exception_info.value.reason == "deadline exceeded"
        assert exception_info.value.__cause__ is timeout

    def test_a_model_returning_nothing_parseable_fails_rather_than_yielding_an_empty_read(
        self, extractor, request_dto
    ):
        # Act & Assert
        with patch(RENDER_PAGE_IMAGES, return_value=([b"page"], 1)):
            with patch(GENERATE_PARSED, return_value=None):
                with pytest.raises(ExtractionFailed) as exception_info:
                    extractor.extract_document_record(request=request_dto)
        assert "no readable response" in exception_info.value.reason

    def test_a_missing_api_key_names_the_variable_rather_than_leaking_a_library_error(
        self, settings
    ):
        # Arrange
        from document_extraction.adapters.gemini_client import (
            get_gemini_client,
            reset_gemini_client,
        )

        settings.GEMINI_API_KEY = ""
        reset_gemini_client()

        # Act & Assert
        with pytest.raises(ExtractionCredentialMissing) as exception_info:
            get_gemini_client()
        assert exception_info.value.variable_name == GEMINI_API_KEY_VARIABLE


    def test_a_type_with_no_registered_read_is_refused_before_any_model_call(
        self, extractor, request_dto
    ):
        # Arrange — a catalog type flipped to implemented without a read module is a
        # wiring mistake, and must never fall through to another type's prompt.
        request = ExtractDocumentRequestDTO(
            filename=request_dto.filename,
            application_id=request_dto.application_id,
            source=request_dto.source,
            file_path=request_dto.file_path,
            document_type_id="tax_receipt",
        )

        # Act & Assert
        with patch(GENERATE_PARSED) as generate:
            with pytest.raises(DocumentReadNotRegistered) as exception_info:
                extractor.extract_document_record(request=request)
        generate.assert_not_called()
        assert exception_info.value.document_type_id == "tax_receipt"

    def test_an_unclassified_request_is_refused_rather_than_read_as_a_pan(
        self, extractor, request_dto
    ):
        # Arrange — reading with no decided type is the silent-misread hazard
        request = ExtractDocumentRequestDTO(
            filename=request_dto.filename,
            application_id=request_dto.application_id,
            source=request_dto.source,
            file_path=request_dto.file_path,
        )

        # Act & Assert
        with patch(GENERATE_PARSED) as generate:
            with pytest.raises(DocumentReadNotRegistered):
                extractor.extract_document_record(request=request)
        generate.assert_not_called()


class TestGeminiDocumentExtractorClassification:
    def test_a_model_naming_a_type_the_catalog_does_not_know_falls_back_to_unknown(
        self, extractor, request_dto
    ):
        # Arrange
        identification = DocumentIdentification(
            document_type_id="ration_card", confidence=0.7
        )

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=([b"page"], 1)):
            with patch(GENERATE_PARSED, return_value=identification):
                classification = extractor.classify_document(request=request_dto)

        # Assert
        assert classification.document_type_id == "unknown"
        assert classification.implemented is False

    def test_a_declared_but_unimplemented_type_is_reported_as_such(
        self, extractor, request_dto
    ):
        # Arrange — AC10
        identification = DocumentIdentification(
            document_type_id="tax_receipt", confidence=0.96
        )

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=([b"page"], 1)):
            with patch(GENERATE_PARSED, return_value=identification):
                classification = extractor.classify_document(request=request_dto)

        # Assert
        assert classification.document_type_id == "tax_receipt"
        assert classification.document_type_label == "Property tax receipt"
        assert classification.implemented is False
        assert classification.type_confidence == 0.96

    def test_a_pan_is_reported_as_implemented(self, extractor, request_dto):
        # Arrange
        identification = DocumentIdentification(document_type_id="pan", confidence=0.99)

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=([b"page"], 1)):
            with patch(GENERATE_PARSED, return_value=identification):
                classification = extractor.classify_document(request=request_dto)

        # Assert
        assert classification.document_type_id == "pan"
        assert classification.implemented is True

    def test_a_page_count_above_the_cap_is_reported_alongside_what_was_processed(
        self, extractor, request_dto, settings
    ):
        # Arrange
        settings.MAX_DOCUMENT_PAGES = 2
        identification = DocumentIdentification(document_type_id="pan", confidence=0.99)

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=([b"page", b"page"], 9)):
            with patch(GENERATE_PARSED, return_value=identification):
                classification = extractor.classify_document(request=request_dto)

        # Assert
        assert classification.page_count == 2
        assert classification.total_page_count == 9

    def test_the_model_is_offered_a_closed_list_of_catalog_types_to_choose_from(
        self, extractor, request_dto
    ):
        # Arrange — the closed list is what stops the model inventing a type id
        identification = DocumentIdentification(document_type_id="pan", confidence=0.99)

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=([b"page"], 1)):
            with patch(GENERATE_PARSED, return_value=identification):
                with patch(BUILD_TEXT_PART, return_value="prompt") as build_text:
                    extractor.classify_document(request=request_dto)

        # Assert
        prompt = build_text.call_args.kwargs["text"]
        assert "- pan: PAN" in prompt
        assert "- aadhaar: Aadhaar" in prompt
        assert "- sale_deed: Sale deed" in prompt
        assert "unknown" in prompt

    def test_a_real_read_maps_through_to_the_record_contract(self, extractor, request_dto):
        # Arrange
        model_read = PanCardRead(
            name="SRINIVAS RAO KANDULA",
            parent_name="VENKATESWARA RAO KANDULA",
            date_of_birth="1979-08-14",
            pan="DQRPK4831L",
            confidence=0.94,
        )

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=([b"page"], 1)):
            with patch(GENERATE_PARSED, return_value=model_read):
                record = extractor.extract_document_record(request=request_dto)

        # Assert
        assert {read.key for read in record.field_reads} == {
            "name",
            "parentName",
            "dob",
            "pan",
        }
        assert record.page_count == 1


SALE_DEED = DocumentTypeEnum.SALE_DEED.value
LINK_DOCUMENT = DocumentTypeEnum.LINK_DOCUMENT.value


def deed_request(tmp_path, page_start=None, page_end=None, document_type_id=None):
    from document_extraction.dtos.extraction_dtos import ExtractDocumentRequestDTO

    stored_file = tmp_path / "01_clean_chain.pdf"
    stored_file.write_bytes(b"not-a-real-pdf")
    return ExtractDocumentRequestDTO(
        filename="01_clean_chain.pdf",
        application_id="BN/2026/0455",
        source=DocumentSource.UPLOAD.value,
        file_path=str(stored_file),
        document_type_id=document_type_id,
        page_start=page_start,
        page_end=page_end,
    )


def page_map(*starts_new_document_by_page):
    from document_extraction.adapters.reads.file_inventory_read import (
        PageLabel,
        PageMap,
    )

    return PageMap(
        pages=[
            PageLabel(
                page=page,
                starts_new_document=starts,
                doc_type="Sale Deed" if starts else None,
            )
            for page, starts in enumerate(starts_new_document_by_page)
        ]
    )


SIX_PAGES = [f"page-{index}".encode() for index in range(6)]


class TestFindingSeveralDocumentsInOneFile:
    def test_a_multi_page_deed_file_is_inventoried_page_by_page(
        self, extractor, tmp_path
    ):
        # Arrange
        request = deed_request(tmp_path)
        answers = [
            DocumentIdentification(document_type_id=SALE_DEED, confidence=0.94),
            page_map(True, False, True, False, True, False),
        ]

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=(SIX_PAGES, 6)):
            with patch(GENERATE_PARSED, side_effect=answers):
                classification = extractor.classify_document(request=request)

        # Assert
        assert classification.is_bundle is True
        assert [
            (segment.page_start, segment.page_end)
            for segment in classification.segments
        ] == [(0, 1), (2, 3), (4, 5)]

    def test_every_deed_but_the_last_is_named_a_link_document(
        self, extractor, tmp_path
    ):
        # Arrange
        request = deed_request(tmp_path)
        answers = [
            DocumentIdentification(document_type_id=SALE_DEED, confidence=0.94),
            page_map(True, False, True, False, True, False),
        ]

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=(SIX_PAGES, 6)):
            with patch(GENERATE_PARSED, side_effect=answers):
                classification = extractor.classify_document(request=request)

        # Assert
        assert [
            segment.document_type_id for segment in classification.segments
        ] == [LINK_DOCUMENT, LINK_DOCUMENT, SALE_DEED]

    def test_each_document_found_is_named_in_the_catalogs_own_words(
        self, extractor, tmp_path
    ):
        # Arrange
        request = deed_request(tmp_path)
        answers = [
            DocumentIdentification(document_type_id=SALE_DEED, confidence=0.94),
            page_map(True, False, True, False),
        ]

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=(SIX_PAGES[:4], 4)):
            with patch(GENERATE_PARSED, side_effect=answers):
                classification = extractor.classify_document(request=request)

        # Assert
        assert [
            segment.document_type_label for segment in classification.segments
        ] == ["Link document", "Sale deed"]

    def test_a_single_page_file_is_not_worth_a_second_model_call(
        self, extractor, request_dto
    ):
        """One page cannot hold two registered documents."""
        # Arrange
        answers = [DocumentIdentification(document_type_id=PAN, confidence=0.99)]

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=([b"page-0"], 1)):
            with patch(GENERATE_PARSED, side_effect=answers) as generate:
                classification = extractor.classify_document(request=request_dto)

        # Assert
        assert generate.call_count == 1
        assert classification.is_bundle is False

    def test_a_card_is_never_inventoried_however_many_pages_it_has(self, extractor, tmp_path):
        """A two-sided card scanned onto two pages is still one card."""
        # Arrange
        from document_extraction.dtos.extraction_dtos import ExtractDocumentRequestDTO

        stored_file = tmp_path / "aadhaar.pdf"
        stored_file.write_bytes(b"not-a-real-pdf")
        request = ExtractDocumentRequestDTO(
            filename="aadhaar.pdf",
            application_id="BN/2026/0421",
            source=DocumentSource.UPLOAD.value,
            file_path=str(stored_file),
        )
        answers = [
            DocumentIdentification(
                document_type_id=DocumentTypeEnum.AADHAAR.value, confidence=0.98
            )
        ]

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=(SIX_PAGES[:2], 2)):
            with patch(GENERATE_PARSED, side_effect=answers) as generate:
                classification = extractor.classify_document(request=request)

        # Assert
        assert generate.call_count == 1
        assert classification.is_bundle is False
        assert len(classification.segments) == 1

    def test_a_file_holding_one_deed_reports_one_document_spanning_it(
        self, extractor, tmp_path
    ):
        # Arrange
        request = deed_request(tmp_path)
        answers = [
            DocumentIdentification(document_type_id=SALE_DEED, confidence=0.98),
            page_map(True, False, False, False, False, False),
        ]

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=(SIX_PAGES, 6)):
            with patch(GENERATE_PARSED, side_effect=answers):
                classification = extractor.classify_document(request=request)

        # Assert
        assert classification.is_bundle is False
        assert (
            classification.segments[0].page_start,
            classification.segments[0].page_end,
        ) == (0, 5)


class TestReadingOneDocumentOutOfABundledFile:
    def test_only_the_documents_own_pages_are_sent_to_the_model(
        self, extractor, tmp_path
    ):
        # Arrange
        request = deed_request(
            tmp_path, page_start=2, page_end=3, document_type_id=LINK_DOCUMENT
        )

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=(SIX_PAGES, 6)):
            with patch(BUILD_IMAGE_PARTS, return_value=[]) as build_parts:
                with patch(GENERATE_PARSED, return_value=_deed_read()):
                    record = extractor.extract_document_record(request=request)

        # Assert
        build_parts.assert_called_once_with([b"page-2", b"page-3"])
        assert record.page_count == 2

    def test_a_slice_is_never_segmented_again(self, extractor, tmp_path):
        """The pass that carved it out already did that work."""
        # Arrange
        request = deed_request(tmp_path, page_start=0, page_end=1)
        answers = [DocumentIdentification(document_type_id=SALE_DEED, confidence=0.9)]

        # Act
        with patch(RENDER_PAGE_IMAGES, return_value=(SIX_PAGES, 6)):
            with patch(GENERATE_PARSED, side_effect=answers) as generate:
                classification = extractor.classify_document(request=request)

        # Assert
        assert generate.call_count == 1
        assert classification.is_bundle is False
        assert classification.page_count == 2

    def test_pages_that_are_not_in_the_file_are_reported_not_guessed(
        self, extractor, tmp_path
    ):
        """Reading the wrong deed silently is the one outcome that must not happen."""
        # Arrange
        request = deed_request(
            tmp_path, page_start=8, page_end=9, document_type_id=LINK_DOCUMENT
        )

        # Act & Assert
        with patch(RENDER_PAGE_IMAGES, return_value=(SIX_PAGES, 6)):
            with patch(GENERATE_PARSED) as generate:
                with pytest.raises(ExtractionFailed) as exception_info:
                    extractor.extract_document_record(request=request)
        generate.assert_not_called()
        assert "Pages 9-10 are not in this file" in exception_info.value.reason


def _deed_read():
    from document_extraction.adapters.reads.deed_read import DeedRead

    return DeedRead(doc_no="2451/2011", sro="Serilingampally")
