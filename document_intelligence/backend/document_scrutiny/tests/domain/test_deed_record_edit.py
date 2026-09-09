from document_extraction.dtos.deed_record_dtos import (
    DeedRecordDTO,
    PartyDTO,
    PropertyInfoDTO,
)
from document_scrutiny.constants.deed_edit_constants import (
    DEED_FIELD_TO_RECORD_PATH,
)
from document_scrutiny.domain.deed_record_edit import DeedRecordEdit


def deed_record() -> DeedRecordDTO:
    return DeedRecordDTO(
        doc_no="5820/2019",
        sro="SRO Serilingampally",
        registration_date="2019-02-18",
        deed_type="Sale Deed",
        sellers=(PartyDTO(name="Sunita Sharma", relative_name="Anil Sharma"),),
        buyers=(PartyDTO(name="Prakash Iyer"),),
        property_info=PropertyInfoDTO(
            survey_no="142/2",
            plot_no="17",
            extent_text="400 Sq. Yards",
            extent_sq_yard=400.0,
            locality="Kondapur",
        ),
        prior_deed_refs=("2451/2011",),
    )


class TestCarryingAnEditIntoTheRecord:
    def test_a_corrected_vendor_reaches_the_seller_name(self):
        # Act
        updated = DeedRecordEdit.apply(
            deed_record=deed_record(), field_key="vendor", value="Sunita Sharman"
        )

        # Assert
        assert updated.sellers[0].name == "Sunita Sharman"

    def test_the_rest_of_the_seller_survives_a_name_edit(self):
        """Only the name was corrected; the father's name that disambiguates them stays."""
        # Act
        updated = DeedRecordEdit.apply(
            deed_record=deed_record(), field_key="vendor", value="Sunita Sharman"
        )

        # Assert
        assert updated.sellers[0].relative_name == "Anil Sharma"

    def test_a_corrected_purchaser_reaches_the_buyer_name(self):
        # Act
        updated = DeedRecordEdit.apply(
            deed_record=deed_record(), field_key="purchaser", value="Prakash R Iyer"
        )

        # Assert
        assert updated.buyers[0].name == "Prakash R Iyer"

    def test_a_corrected_survey_number_reaches_the_property(self):
        # Act
        updated = DeedRecordEdit.apply(
            deed_record=deed_record(), field_key="surveyNo", value="142/3"
        )

        # Assert
        assert updated.property_info.survey_no == "142/3"

    def test_a_corrected_village_reaches_the_locality(self):
        # Act
        updated = DeedRecordEdit.apply(
            deed_record=deed_record(), field_key="village", value="Gachibowli"
        )

        # Assert
        assert updated.property_info.locality == "Gachibowli"

    def test_a_corrected_document_number_reaches_the_record(self):
        # Act
        updated = DeedRecordEdit.apply(
            deed_record=deed_record(), field_key="docNo", value="5820/2020"
        )

        # Assert
        assert updated.doc_no == "5820/2020"


class TestCorrectingTheExtent:
    def test_the_words_the_officer_typed_are_kept(self):
        # Act
        updated = DeedRecordEdit.apply(
            deed_record=deed_record(),
            field_key="extent",
            value="600 Sq. Yards (501.67 Sq. Metres)",
        )

        # Assert
        assert updated.property_info.extent_text == "600 Sq. Yards (501.67 Sq. Metres)"

    def test_the_number_the_chain_measures_on_is_re_derived(self):
        """A corrected extent must move the figure the chain's arithmetic uses, or the
        chain keeps measuring against the misread area."""
        # Act
        updated = DeedRecordEdit.apply(
            deed_record=deed_record(),
            field_key="extent",
            value="600 Sq. Yards (501.67 Sq. Metres)",
        )

        # Assert
        assert updated.property_info.extent_sq_yard == 600.0

    def test_an_unreadable_extent_clears_the_number_rather_than_keeping_a_stale_one(
        self,
    ):
        # Act
        updated = DeedRecordEdit.apply(
            deed_record=deed_record(), field_key="extent", value="see schedule"
        )

        # Assert
        assert updated.property_info.extent_sq_yard is None


class TestEditsThatDoNotTouchTheRecord:
    def test_a_boundaries_edit_leaves_the_record_untouched(self):
        """The chain does not trace on boundaries, so the record has nothing to change."""
        # Arrange
        record = deed_record()

        # Act
        updated = DeedRecordEdit.apply(
            deed_record=record, field_key="boundaries", value="North: road"
        )

        # Assert
        assert updated == record

    def test_a_consideration_edit_leaves_the_record_untouched(self):
        # Arrange
        record = deed_record()

        # Act
        updated = DeedRecordEdit.apply(
            deed_record=record, field_key="consideration", value="Rs 1"
        )

        # Assert
        assert updated == record

    def test_a_document_that_is_not_a_deed_has_no_record_to_edit(self):
        """A PAN edit passes a None record through untouched rather than crashing."""
        # Act & Assert
        assert (
            DeedRecordEdit.apply(deed_record=None, field_key="name", value="X") is None
        )


class TestNotInventingWhatTheDeedNeverHad:
    def test_a_vendor_edit_on_a_deed_read_with_no_seller_changes_nothing(self):
        """Fabricating a party would put a name in the chain the paper never carried."""
        # Arrange
        record = DeedRecordDTO(doc_no="1/2000", sellers=(), buyers=())

        # Act
        updated = DeedRecordEdit.apply(
            deed_record=record, field_key="vendor", value="Somebody"
        )

        # Assert
        assert updated.sellers == ()


class TestTheMapCannotDriftFromTheReadSpec:
    def test_every_edited_deed_field_lands_where_the_read_put_it(self):
        """The map is the inverse of extraction's _SHARED_FIELD_KEYS. Pin each entry
        against the read spec so the two can never quietly disagree — the DTO renames
        `property` to `property_info` to avoid shadowing the builtin, hence the swap."""
        # Arrange
        from document_extraction.adapters.reads.deed_read import SALE_DEED_READ

        path_by_field_key = {
            field_key: attribute.replace("property.", "property_info.")
            for attribute, field_key in SALE_DEED_READ.field_keys_by_attribute.items()
        }

        # Assert
        for field_key, path in DEED_FIELD_TO_RECORD_PATH.items():
            assert path == path_by_field_key[field_key], field_key
