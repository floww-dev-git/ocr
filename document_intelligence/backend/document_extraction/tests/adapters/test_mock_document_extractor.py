import pytest

from document_extraction.constants.extraction_constants import (
    KEYWORD_MATCH_TYPE_CONFIDENCE,
    UNRECOGNISED_TYPE_CONFIDENCE,
    DocumentSource,
)
from document_extraction.dtos.extraction_dtos import ExtractDocumentRequestDTO
from document_extraction.exceptions.extraction_exceptions import (
    NoSampleReadForApplication,
)

CLEAN_APPLICATION_ID = "BN/2026/0421"
MISMATCH_APPLICATION_ID = "BN/2026/0377"


def build_request(
    filename: str = "pan_card.pdf",
    application_id: str = CLEAN_APPLICATION_ID,
    source: str = DocumentSource.SAMPLE.value,
    document_type_id: str = "pan",
) -> ExtractDocumentRequestDTO:
    return ExtractDocumentRequestDTO(
        filename=filename,
        application_id=application_id,
        source=source,
        document_type_id=document_type_id,
    )


class TestMockDocumentExtractor:
    @pytest.fixture
    def extractor(self):
        from document_extraction.adapters.mock_document_extractor import MockDocumentExtractor

        return MockDocumentExtractor()

    def test_a_filename_matching_no_keyword_is_classified_unknown(self, extractor):
        # Arrange — AC10 depends on never guessing PAN from an unrecognisable name
        request = build_request(filename="scan_0001.pdf")

        # Act
        classification = extractor.classify_document(request=request)

        # Assert
        assert classification.document_type_id == "unknown"
        assert classification.implemented is False
        assert classification.type_confidence == UNRECOGNISED_TYPE_CONFIDENCE

    def test_a_filename_naming_an_unimplemented_type_is_classified_as_that_type(
        self, extractor
    ):
        # Arrange — AC10
        request = build_request(filename="property_tax_receipt.pdf")

        # Act
        classification = extractor.classify_document(request=request)

        # Assert
        assert classification.document_type_id == "tax_receipt"
        assert classification.document_type_label == "Property tax receipt"
        assert classification.implemented is False

    def test_extracting_for_an_application_with_no_sample_read_raises(self, extractor):
        # Arrange
        request = build_request(application_id="BN/2026/9999")

        # Act & Assert
        with pytest.raises(NoSampleReadForApplication) as exception_info:
            extractor.extract_document_record(request=request)
        assert exception_info.value.application_id == "BN/2026/9999"

    def test_the_first_matching_keyword_wins(self, extractor):
        # Arrange — "aadhaar" is ordered before "pan" in the catalog's rules
        request = build_request(filename="aadhaar_and_pan.pdf")

        # Act
        classification = extractor.classify_document(request=request)

        # Assert
        assert classification.document_type_id == "aadhaar"

    @pytest.mark.parametrize(
        "filename", ["pan_card.pdf", "PAN.JPG", "applicant-pan-front.png"]
    )
    def test_a_filename_naming_a_pan_is_classified_as_pan(self, extractor, filename):
        # Arrange
        request = build_request(filename=filename)

        # Act
        classification = extractor.classify_document(request=request)

        # Assert
        assert classification.document_type_id == "pan"
        assert classification.document_type_label == "PAN"
        assert classification.implemented is True

    def test_an_uploaded_pan_is_classified_with_the_keyword_match_confidence(
        self, extractor
    ):
        # Arrange
        request = build_request(source=DocumentSource.UPLOAD.value)

        # Act
        classification = extractor.classify_document(request=request)

        # Assert
        assert classification.type_confidence == KEYWORD_MATCH_TYPE_CONFIDENCE

    def test_a_sample_read_reports_the_canned_type_confidence(self, extractor):
        # Arrange
        request = build_request(source=DocumentSource.SAMPLE.value)

        # Act
        classification = extractor.classify_document(request=request)

        # Assert
        assert classification.type_confidence == 0.99

    def test_reads_the_canned_pan_for_the_clean_application(self, extractor):
        # Arrange — AC1
        request = build_request()

        # Act
        record = extractor.extract_document_record(request=request)

        # Assert
        assert {read.key: read.value for read in record.field_reads} == {
            "name": "SRINIVAS RAO KANDULA",
            "parentName": "VENKATESWARA RAO KANDULA",
            "dob": "1979-08-14",
            "pan": "DQRPK4831L",
        }
        assert record.structure_findings == {
            "photo": True,
            "signature": True,
            "hologram": True,
        }
        assert record.page_count == 1

    def test_reads_the_dropped_letter_in_the_seeded_mismatch_application(self, extractor):
        # Arrange — AC2: the canned read is the source of the seeded name warning
        request = build_request(application_id=MISMATCH_APPLICATION_ID)

        # Act
        record = extractor.extract_document_record(request=request)

        # Assert
        reads_by_key = {read.key: read for read in record.field_reads}
        assert reads_by_key["name"].value == "MOHAMMED IRFAN SIDDIQI"
        assert reads_by_key["pan"].value == "BNMPS7720K"

    @pytest.mark.parametrize(
        "filename",
        ["irrigation_noc.pdf", "IRRIGATION-NOC.PDF", "ftl_clearance_letter.pdf"],
    )
    def test_a_filename_naming_an_irrigation_clearance_is_classified_as_one(
        self, extractor, filename
    ):
        # Arrange — "ftl" names the full tank level the clearance is about
        request = build_request(filename=filename, document_type_id="irrigation_noc")

        # Act
        classification = extractor.classify_document(request=request)

        # Assert
        assert classification.document_type_id == "irrigation_noc"
        assert classification.document_type_label == "Irrigation NOC"
        assert classification.implemented is True

    def test_reads_the_canned_irrigation_noc_for_the_seeded_application(
        self, extractor
    ):
        # Arrange
        request = build_request(
            filename="irrigation_noc.pdf",
            application_id=MISMATCH_APPLICATION_ID,
            document_type_id="irrigation_noc",
        )

        # Act
        record = extractor.extract_document_record(request=request)

        # Assert — the canned keys are exactly the catalog's, so a mock run and a
        # real one produce the same checks
        assert {read.key: read.value for read in record.field_reads} == {
            "nocNo": "IRR/NOC/2026/0093",
            "issuedBy": "Irrigation and CAD Department",
            "issueDate": "2026-04-10",
            "validUpto": "2028-04-09",
            "applicant": "Mohammed Irfan Siddiqui",
            "surveyNo": "77/2",
            "bufferCondition": (
                "Site lies outside the FTL buffer. No construction within 9 m of "
                "the tank bund."
            ),
        }
        assert record.structure_findings == {"seal": True, "signature": True}
        assert record.page_count == 2

    def test_the_canned_noc_for_the_clean_application_has_lapsed(self, extractor):
        # Arrange — the seeded lapse behind the expired-clearance story
        request = build_request(
            filename="irrigation_noc.pdf", document_type_id="irrigation_noc"
        )

        # Act
        record = extractor.extract_document_record(request=request)

        # Assert
        reads_by_key = {read.key: read for read in record.field_reads}
        assert reads_by_key["validUpto"].value == "2026-05-21"
        assert reads_by_key["surveyNo"].value == "118/2"

    @pytest.mark.parametrize(
        "filename, expected_type",
        [
            ("encumbrance_certificate.pdf", "ec"),
            ("land_conversion_certificate.pdf", "conversion_cert"),
            ("nala_order.pdf", "conversion_cert"),
            ("market_value_certificate.pdf", "market_value_cert"),
            ("mvc_2026.pdf", "market_value_cert"),
            ("pattadar_passbook.pdf", "pattadar_passbook"),
            ("dharani_passbook.pdf", "pattadar_passbook"),
            ("occupancy_rights_certificate.pdf", "orc"),
            ("inam_orc.pdf", "orc"),
        ],
    )
    def test_a_filename_naming_a_land_document_is_classified_as_one(
        self, extractor, filename, expected_type
    ):
        # Arrange
        request = build_request(filename=filename, document_type_id=expected_type)

        # Act
        classification = extractor.classify_document(request=request)

        # Assert
        assert classification.document_type_id == expected_type
        assert classification.implemented is True

    @pytest.mark.parametrize(
        "document_type_id, expected_fields",
        [
            (
                "ec",
                {
                    "ecNo": "EC/2026/GDP/04412",
                    "period": "01-01-2000 to 31-12-2025",
                    "surveyNo": "77/2",
                    "owner": "Mohammed Irfan Siddiqui",
                    "encumbrances": (
                        "No subsisting encumbrances found for the period searched."
                    ),
                },
            ),
            (
                "conversion_cert",
                {
                    "conversionOrderNo": "RDO/NALA/2025/0731",
                    "issuedBy": "Revenue Divisional Officer, Rajendranagar",
                    "issueDate": "2025-11-18",
                    "applicant": "Mohammed Irfan Siddiqui",
                    "surveyNo": "77/2",
                    "village": "Kokapet",
                    "extent": "420 sq. yds",
                    "convertedUse": "Commercial",
                    "nalaAssessment": "Rs. 1,05,000",
                },
            ),
            (
                "orc",
                {
                    "orcNo": "RDO/ORC/2024/0155",
                    "issuedBy": "Revenue Divisional Officer, Chevella",
                    "issueDate": "2024-09-30",
                    "occupant": "Mohammed Irfan Siddiqui",
                    "surveyNo": "77/2",
                    "village": "Kokapet",
                    "extent": "420 sq. yds",
                    "inamCategory": "Service Inam",
                },
            ),
        ],
    )
    def test_reads_the_canned_land_document_for_the_seeded_application(
        self, extractor, document_type_id, expected_fields
    ):
        # Arrange — canned keys are exactly the catalog's, so mock and real reads agree
        request = build_request(
            filename=f"{document_type_id}.pdf",
            application_id=MISMATCH_APPLICATION_ID,
            document_type_id=document_type_id,
        )

        # Act
        record = extractor.extract_document_record(request=request)

        # Assert
        assert {read.key: read.value for read in record.field_reads} == expected_fields

    def test_the_pattadar_passbook_reads_a_smaller_extent_than_the_application(
        self, extractor
    ):
        # Arrange — the seeded revenue-vs-application discrepancy (390 vs 420)
        request = build_request(
            filename="pattadar_passbook.pdf",
            application_id=MISMATCH_APPLICATION_ID,
            document_type_id="pattadar_passbook",
        )

        # Act
        record = extractor.extract_document_record(request=request)

        # Assert
        reads_by_key = {read.key: read.value for read in record.field_reads}
        assert reads_by_key["extent"] == "390 sq. yds"
        assert reads_by_key["pattadar"] == "Mohammed Irfan Siddiqui"
        assert record.structure_findings == {
            "photo": True,
            "seal": True,
            "signature": True,
        }

    def test_reads_the_canned_market_value_certificate(self, extractor):
        # Arrange
        request = build_request(
            filename="market_value_certificate.pdf",
            application_id=MISMATCH_APPLICATION_ID,
            document_type_id="market_value_cert",
        )

        # Act
        record = extractor.extract_document_record(request=request)

        # Assert
        reads_by_key = {read.key: read.value for read in record.field_reads}
        assert reads_by_key["marketValuePerSqYd"] == "Rs. 45,000 per sq. yd"
        assert reads_by_key["surveyNo"] == "77/2"

    def test_an_uploaded_read_carries_discounted_field_confidences(self, extractor):
        # Arrange
        sample_request = build_request(source=DocumentSource.SAMPLE.value)
        upload_request = build_request(source=DocumentSource.UPLOAD.value)

        # Act
        sample_record = extractor.extract_document_record(request=sample_request)
        upload_record = extractor.extract_document_record(request=upload_request)

        # Assert
        sample_confidences = {read.key: read.confidence for read in sample_record.field_reads}
        upload_confidences = {read.key: read.confidence for read in upload_record.field_reads}
        assert sample_confidences == {
            "name": 0.98,
            "parentName": 0.96,
            "dob": 0.99,
            "pan": 0.99,
        }
        assert upload_confidences == {
            "name": 0.83,
            "parentName": 0.82,
            "dob": 0.84,
            "pan": 0.84,
        }

    def test_every_read_field_carries_a_provenance_box(self, extractor):
        # Arrange
        request = build_request()

        # Act
        record = extractor.extract_document_record(request=request)

        # Assert
        boxed_field_keys = {box.field_key for box in record.boxes}
        read_field_keys = {read.key for read in record.field_reads}
        assert boxed_field_keys == read_field_keys
        for box in record.boxes:
            assert box.page == 0
            assert len(box.box) == 4
            assert all(0 <= coordinate <= 1000 for coordinate in box.box)

    def test_the_record_reports_its_weakest_field_as_the_overall_confidence(
        self, extractor
    ):
        # Arrange
        request = build_request()

        # Act
        record = extractor.extract_document_record(request=request)

        # Assert
        assert record.overall_confidence == 0.96
        assert record.low_confidence_fields == ()


BUNDLE_APPLICATION_ID = "BN/2026/0455"
CLEAN_CHAIN = "01_clean_chain.pdf"


def bundle_request(page_start=None, page_end=None, document_type_id=None):
    from document_extraction.constants.extraction_constants import DocumentSource
    from document_extraction.dtos.extraction_dtos import ExtractDocumentRequestDTO

    return ExtractDocumentRequestDTO(
        filename=CLEAN_CHAIN,
        application_id=BUNDLE_APPLICATION_ID,
        source=DocumentSource.UPLOAD.value,
        document_type_id=document_type_id,
        page_start=page_start,
        page_end=page_end,
    )


class TestABundledDeedFileOffline:
    @pytest.fixture
    def extractor(self):
        from document_extraction.adapters.mock_document_extractor import (
            MockDocumentExtractor,
        )

        return MockDocumentExtractor()

    def test_a_bundle_is_recognised_by_its_whole_name_not_a_keyword(self, extractor):
        """A bundle is a specific file, not a kind of file — and none of the shipped
        bundle names contains a document-type keyword."""
        # Act
        classification = extractor.classify_document(request=bundle_request())

        # Assert
        assert classification.document_type_id == "sale_deed"
        assert classification.is_bundle is True

    def test_every_deed_inside_is_located_by_page(self, extractor):
        # Act
        classification = extractor.classify_document(request=bundle_request())

        # Assert
        assert [
            (segment.page_start, segment.page_end)
            for segment in classification.segments
        ] == [(0, 1), (2, 3), (4, 5)]
        assert classification.page_count == 6

    def test_only_the_deed_being_relied_on_is_the_sale_deed(self, extractor):
        # Act
        classification = extractor.classify_document(request=bundle_request())

        # Assert
        assert [
            segment.document_type_id for segment in classification.segments
        ] == ["link_doc", "link_doc", "sale_deed"]

    def test_a_slice_is_identified_as_what_the_inventory_already_called_it(
        self, extractor
    ):
        # Act
        classification = extractor.classify_document(
            request=bundle_request(page_start=2, page_end=3)
        )

        # Assert
        assert classification.document_type_id == "link_doc"
        assert classification.page_count == 2

    def test_a_slice_is_never_segmented_again(self, extractor):
        # Act
        classification = extractor.classify_document(
            request=bundle_request(page_start=0, page_end=1)
        )

        # Assert
        assert classification.is_bundle is False

    def test_each_slice_reads_back_the_deed_printed_on_those_pages(self, extractor):
        # Act
        records = [
            extractor.extract_document_record(
                request=bundle_request(
                    page_start=page_start,
                    page_end=page_start + 1,
                    document_type_id="link_doc",
                )
            )
            for page_start in (0, 2, 4)
        ]

        # Assert
        assert [record.deed_record.doc_no for record in records] == [
            "1188/2003",
            "2451/2011",
            "5820/2019",
        ]

    def test_a_slice_read_offline_carries_the_structure_the_chain_needs(
        self, extractor
    ):
        """Without party lists and recital citations there is nothing to trace."""
        # Act
        record = extractor.extract_document_record(
            request=bundle_request(page_start=4, page_end=5, document_type_id="sale_deed")
        )

        # Assert
        assert record.deed_record.sellers[0].name == "Sunita Sharma"
        assert record.deed_record.buyers[0].name == "Prakash Iyer"
        assert record.deed_record.prior_deed_refs == ("2451/2011",)
