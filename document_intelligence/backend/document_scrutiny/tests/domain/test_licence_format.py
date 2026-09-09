import pytest

from document_scrutiny.constants.enums import CheckStatus
from document_scrutiny.constants.licence_format_constants import LicenceFormatState
from document_scrutiny.domain.licence_format import LicenceFormat
from document_scrutiny.domain.licence_format_check import LicenceFormatCheck

SEEDED_LICENCE = "TS0920150012345"


class TestLicenceFormat:
    def test_the_seeded_licence_number_reads_as_valid(self):
        # Act
        inspected = LicenceFormat.inspect(licence_number=SEEDED_LICENCE)

        # Assert
        assert inspected.state == LicenceFormatState.RECOGNISED.value
        assert inspected.state_code == "TS"
        assert inspected.issue_year == "2015"

    def test_a_sixteen_character_number_reads_as_valid(self):
        """Offices with a three-digit RTO block issue sixteen characters.
        TS20820220017249 is a real Telangana licence, and rejecting it would report a
        genuine document as forged."""
        # Act
        inspected = LicenceFormat.inspect(licence_number="TS20820220017249")

        # Assert
        assert inspected.state == LicenceFormatState.RECOGNISED.value
        assert inspected.state_code == "TS"
        # Counted from the end, so the wider RTO block does not push the year along.
        assert inspected.issue_year == "2022"

    @pytest.mark.parametrize(
        "printed", ["TS-09 20150012345", "TS 09 2015 0012345", "ts0920150012345"]
    )
    def test_the_ways_a_licence_is_actually_printed_are_all_accepted(self, printed):
        # Arrange — separators and case vary between states and between cards
        # Act
        inspected = LicenceFormat.inspect(licence_number=printed)

        # Assert
        assert inspected.state == LicenceFormatState.RECOGNISED.value
        assert inspected.issue_year == "2015"

    @pytest.mark.parametrize("licence_number", [None, "", "   "])
    def test_nothing_read_is_reported_as_nothing_read(self, licence_number):
        # Act
        inspected = LicenceFormat.inspect(licence_number=licence_number)

        # Assert
        assert inspected.state == LicenceFormatState.MALFORMED.value
        assert "No licence number" in str(inspected.rejection_reason)

    @pytest.mark.parametrize(
        "licence_number,expected_phrase",
        [
            ("TS092015001234", "15 or 16 characters"),
            ("TS092015001234567", "15 or 16 characters"),
            ("T09920150012345", "two-letter state code"),
            ("TSX920150012345", "two-letter state code"),
            ("731655204821345", "two-letter state code"),
        ],
    )
    def test_a_number_of_the_wrong_shape_is_refused_and_says_why(
        self, licence_number, expected_phrase
    ):
        # Act
        inspected = LicenceFormat.inspect(licence_number=licence_number)

        # Assert
        assert inspected.state == LicenceFormatState.MALFORMED.value
        assert expected_phrase in str(inspected.rejection_reason)

    def test_an_impossible_year_of_issue_warns_rather_than_failing(self):
        # Arrange — the shape is right, so the number is probably real and misread
        # Act
        inspected = LicenceFormat.inspect(licence_number="TS0900010012345")

        # Assert
        assert inspected.state == LicenceFormatState.IMPLAUSIBLE_YEAR.value
        assert inspected.issue_year == "0001"

    def test_a_pan_is_not_mistaken_for_a_licence(self):
        # Act
        inspected = LicenceFormat.inspect(licence_number="DQRPK4831L")

        # Assert
        assert inspected.state == LicenceFormatState.MALFORMED.value


class TestLicenceFormatCheck:
    def test_a_valid_licence_number_passes_and_reports_what_it_read(self):
        # Act
        check = LicenceFormatCheck.build(
            document_id="document_1",
            field_key="dlNo",
            licence_number=SEEDED_LICENCE,
        )

        # Assert
        assert check.status == CheckStatus.PASS.value
        assert check.check_id == "document_1:licence-format"
        assert check.field_key == "dlNo"
        assert "2015" in check.detail
        assert "TS" in check.detail

    def test_a_malformed_licence_number_fails_and_carries_the_reason(self):
        # Act
        check = LicenceFormatCheck.build(
            document_id="document_1", field_key="dlNo", licence_number="TS09"
        )

        # Assert
        assert check.status == CheckStatus.FAIL.value
        assert "15 or 16 characters" in check.detail

    def test_an_impossible_year_warns(self):
        # Act
        check = LicenceFormatCheck.build(
            document_id="document_1",
            field_key="dlNo",
            licence_number="TS0900010012345",
        )

        # Assert
        assert check.status == CheckStatus.WARN.value
        assert "0001" in check.detail
