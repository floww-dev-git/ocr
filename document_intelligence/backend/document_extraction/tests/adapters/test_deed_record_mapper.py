import pytest

from document_extraction.adapters.reads.deed_read import (
    LINK_DOCUMENT_READ,
    SALE_DEED_READ,
    DeedFieldBoxRead,
    DeedPartyRead,
    DeedPropertyRead,
    DeedRead,
)
from document_extraction.adapters.reads.deed_record_mapper import DeedRecordMapper
from document_extraction.constants.extraction_constants import DocumentSource


def build_deed_read(**overrides) -> DeedRead:
    defaults = {
        "doc_no": "4821/2019",
        "sro": "SRO Quthbullapur",
        "registration_date": "2019-03-12",
        "execution_date": "2019-03-08",
        "deed_type": "Sale Deed",
        "sellers": [
            DeedPartyRead(
                name="Padmavathi Rentala",
                relation="w/o",
                relative_name="Ravi Rentala",
                pan="AAAPR1234C",
            )
        ],
        "buyers": [DeedPartyRead(name="Srinivas Rao Kandula")],
        "property": DeedPropertyRead(
            survey_no="118/2",
            plot_no="42",
            extent_text="267 sq. yds",
            extent_sqyd=267.0,
            boundaries="North: Plot 41. South: 30 ft road.",
            locality="Bachupally",
        ),
        "consideration_text": "Rs 48,06,000",
        "consideration_inr": 4806000.0,
        "prior_deed_refs": ["2210/2009"],
        "confidence": 0.95,
    }
    defaults.update(overrides)
    return DeedRead(**defaults)


def map_read(model_read: DeedRead, read_spec=SALE_DEED_READ):
    return DeedRecordMapper.to_document_record(
        model_read=model_read,
        read_spec=read_spec,
        source=DocumentSource.SAMPLE.value,
        page_count=14,
    )


class TestDeedRecordMapperFlattensForTheOfficer:
    def test_one_read_fills_every_field_the_sale_deed_declares(self):
        # Act
        record = map_read(build_deed_read())

        # Assert
        assert {read.key: read.value for read in record.field_reads} == {
            "docNo": "4821/2019",
            "regDate": "2019-03-12",
            "sro": "SRO Quthbullapur",
            "vendor": "Padmavathi Rentala",
            "purchaser": "Srinivas Rao Kandula",
            "surveyNo": "118/2",
            "plotNo": "42",
            "extent": "267 sq. yds",
            "village": "Bachupally",
            "consideration": "Rs 48,06,000",
            "boundaries": "North: Plot 41. South: 30 ft road.",
        }

    def test_a_link_document_carries_no_consideration_or_boundaries(self):
        # Arrange — the catalog declares fewer fields on a link document
        # Act
        record = map_read(build_deed_read(), read_spec=LINK_DOCUMENT_READ)

        # Assert
        read_keys = {read.key for read in record.field_reads}
        assert "consideration" not in read_keys
        assert "boundaries" not in read_keys
        assert "docNo" in read_keys
        assert "vendor" in read_keys

    def test_the_first_party_on_each_side_becomes_the_flat_name(self):
        # Arrange — a deed with two sellers still shows one vendor to the officer
        model_read = build_deed_read(
            sellers=[
                DeedPartyRead(name="Padmavathi Rentala"),
                DeedPartyRead(name="Ravi Rentala"),
            ]
        )

        # Act
        record = map_read(model_read)

        # Assert
        flat = {read.key: read.value for read in record.field_reads}
        assert flat["vendor"] == "Padmavathi Rentala"

    def test_a_deed_with_no_parties_read_yields_no_vendor_or_purchaser(self):
        # Arrange — a path that runs out must not raise
        model_read = build_deed_read(sellers=[], buyers=[])

        # Act
        record = map_read(model_read)

        # Assert
        read_keys = {read.key for read in record.field_reads}
        assert "vendor" not in read_keys
        assert "purchaser" not in read_keys
        assert "docNo" in read_keys

    def test_the_four_structural_elements_are_mapped_onto_catalog_keys(self):
        # Act
        record = map_read(build_deed_read(witnesses_present=False))

        # Assert
        assert record.structure_findings == {
            "schedule": True,
            "stamp": True,
            "registration": True,
            "witnesses": False,
        }

    def test_a_link_document_is_not_asked_about_witnesses(self):
        # Act
        record = map_read(build_deed_read(), read_spec=LINK_DOCUMENT_READ)

        # Assert
        assert set(record.structure_findings) == {
            "schedule",
            "stamp",
            "registration",
        }


class TestDeedRecordMapperKeepsTheStructureForTheChain:
    def test_the_structured_record_is_carried_alongside_the_flat_values(self):
        # Act
        record = map_read(build_deed_read())

        # Assert
        deed = record.deed_record
        assert deed is not None
        assert deed.doc_no == "4821/2019"
        assert deed.deed_type == "Sale Deed"
        assert deed.prior_deed_refs == ("2210/2009",)
        assert deed.consideration_inr == 4806000.0
        assert deed.property_info.extent_sq_yard == 267.0

    def test_the_party_details_that_disambiguate_people_survive(self):
        # Arrange — relation and relative name are what tell two namesakes apart
        # Act
        deed = map_read(build_deed_read()).deed_record

        # Assert
        seller = deed.sellers[0]
        assert seller.name == "Padmavathi Rentala"
        assert seller.relation == "w/o"
        assert seller.relative_name == "Ravi Rentala"
        assert seller.pan == "AAAPR1234C"

    def test_every_party_is_kept_not_just_the_first(self):
        # Arrange — the chain matches across whole party lists
        model_read = build_deed_read(
            sellers=[
                DeedPartyRead(name="Padmavathi Rentala"),
                DeedPartyRead(name="Ravi Rentala"),
            ]
        )

        # Act
        deed = map_read(model_read).deed_record

        # Assert
        assert [party.name for party in deed.sellers] == [
            "Padmavathi Rentala",
            "Ravi Rentala",
        ]

    def test_a_party_with_no_name_is_dropped_rather_than_carried_empty(self):
        # Arrange — a nameless party cannot be matched and would inflate the count
        model_read = build_deed_read(
            sellers=[DeedPartyRead(name="   "), DeedPartyRead(name="Ravi Rentala")]
        )

        # Act
        deed = map_read(model_read).deed_record

        # Assert
        assert [party.name for party in deed.sellers] == ["Ravi Rentala"]

    def test_an_unreadable_number_becomes_nothing_rather_than_a_wrong_number(self):
        # Act
        deed = map_read(build_deed_read(consideration_inr=None)).deed_record

        # Assert
        assert deed.consideration_inr is None

    def test_a_deed_executed_through_a_power_of_attorney_says_so(self):
        # Act
        deed = map_read(build_deed_read(executed_via_gpa=True)).deed_record

        # Assert
        assert deed.executed_via_gpa is True

    def test_a_blank_prior_deed_reference_is_dropped(self):
        # Act
        deed = map_read(
            build_deed_read(prior_deed_refs=["2210/2009", "  ", ""])
        ).deed_record

        # Assert
        assert deed.prior_deed_refs == ("2210/2009",)


class TestDeedRecordMapperProvenance:
    def test_the_deeds_own_box_labels_are_mapped_onto_catalog_field_keys(self):
        # Arrange — the deed prompt labels boxes with its own names, not the catalog's
        model_read = build_deed_read(
            boxes=[
                DeedFieldBoxRead(
                    label="doc_no", value="4821/2019", page=0, box=[1, 2, 3, 4]
                ),
                DeedFieldBoxRead(
                    label="seller", value="Padmavathi Rentala", page=1, box=[5, 6, 7, 8]
                ),
                DeedFieldBoxRead(
                    label="survey_no", value="118/2", page=2, box=[9, 10, 11, 12]
                ),
            ]
        )

        # Act
        record = map_read(model_read)

        # Assert
        assert {box.field_key for box in record.boxes} == {
            "docNo",
            "vendor",
            "surveyNo",
        }

    def test_a_box_naming_a_field_this_type_does_not_declare_is_discarded(self):
        # Arrange — a link document has no consideration
        model_read = build_deed_read(
            boxes=[
                DeedFieldBoxRead(
                    label="consideration",
                    value="Rs 48,06,000",
                    page=0,
                    box=[1, 2, 3, 4],
                )
            ]
        )

        # Act
        record = map_read(model_read, read_spec=LINK_DOCUMENT_READ)

        # Assert
        assert record.boxes == ()

    def test_a_box_with_a_label_the_prompt_never_asked_for_is_discarded(self):
        # Arrange
        model_read = build_deed_read(
            boxes=[
                DeedFieldBoxRead(
                    label="stamp_duty", value="Rs 2,000", page=0, box=[1, 2, 3, 4]
                )
            ]
        )

        # Act
        record = map_read(model_read)

        # Assert
        assert record.boxes == ()


class TestDeedRecordMapperConfidence:
    @pytest.mark.parametrize(
        "source,expected",
        [(DocumentSource.SAMPLE.value, 0.95), (DocumentSource.UPLOAD.value, 0.81)],
    )
    def test_an_uploaded_read_is_discounted_like_every_other_type(
        self, source, expected
    ):
        # Act
        record = DeedRecordMapper.to_document_record(
            model_read=build_deed_read(),
            read_spec=SALE_DEED_READ,
            source=source,
            page_count=14,
        )

        # Assert
        assert {read.confidence for read in record.field_reads} == {expected}

    def test_a_field_the_model_doubted_lands_below_the_review_threshold(self):
        # Arrange
        model_read = build_deed_read(low_confidence_fields=["boundaries"])

        # Act
        record = map_read(model_read)

        # Assert
        confidences = {read.key: read.confidence for read in record.field_reads}
        assert confidences["boundaries"] == 0.55
        assert record.low_confidence_fields == ("boundaries",)

    def test_the_page_count_is_carried_from_the_rendered_pages(self):
        # Act
        record = map_read(build_deed_read())

        # Assert
        assert record.page_count == 14
