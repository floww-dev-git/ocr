import pytest

from document_scrutiny.constants.aadhaar_format_constants import AadhaarFormatState
from document_scrutiny.constants.enums import CheckStatus
from document_scrutiny.domain.aadhaar_format import AadhaarFormat
from document_scrutiny.domain.aadhaar_format_check import AadhaarFormatCheck

SEEDED_AADHAAR_NUMBERS = ("731655204821", "409322107754", "551809326604")


class TestAadhaarFormat:
    @pytest.mark.parametrize("aadhaar_number", SEEDED_AADHAAR_NUMBERS)
    def test_every_seeded_application_number_reads_as_valid(self, aadhaar_number):
        # Arrange — a demo where every seeded application reports a forged Aadhaar
        # would be worse than no format check at all
        # Act
        inspected = AadhaarFormat.inspect(aadhaar_number=aadhaar_number)

        # Assert
        assert inspected.state == AadhaarFormatState.RECOGNISED.value
        assert inspected.rejection_reason is None

    def test_the_printed_grouping_is_accepted(self):
        # Arrange — the card prints three groups of four
        # Act
        inspected = AadhaarFormat.inspect(aadhaar_number="7316 5520 4821")

        # Assert
        assert inspected.state == AadhaarFormatState.RECOGNISED.value

    @pytest.mark.parametrize("aadhaar_number", [None, "", "    "])
    def test_nothing_read_is_reported_as_nothing_read(self, aadhaar_number):
        # Act
        inspected = AadhaarFormat.inspect(aadhaar_number=aadhaar_number)

        # Assert
        assert inspected.state == AadhaarFormatState.MALFORMED.value
        assert "No Aadhaar number" in str(inspected.rejection_reason)

    @pytest.mark.parametrize(
        "aadhaar_number,expected_phrase",
        [
            ("73165520482", "twelve digits"),
            ("7316552048211", "twelve digits"),
            ("73165520482X", "twelve digits and nothing else"),
            ("DQRPK4831L", "twelve digits and nothing else"),
        ],
    )
    def test_a_number_of_the_wrong_shape_is_refused_and_says_why(
        self, aadhaar_number, expected_phrase
    ):
        # Act
        inspected = AadhaarFormat.inspect(aadhaar_number=aadhaar_number)

        # Assert
        assert inspected.state == AadhaarFormatState.MALFORMED.value
        assert expected_phrase in str(inspected.rejection_reason)

    @pytest.mark.parametrize("leading_digit", ["0", "1"])
    def test_a_number_uidai_never_issues_is_refused(self, leading_digit):
        # Arrange — a twelve-digit number opening 0 or 1 is some other number
        # Act
        inspected = AadhaarFormat.inspect(
            aadhaar_number=f"{leading_digit}31655204821"
        )

        # Assert
        assert inspected.state == AadhaarFormatState.MALFORMED.value
        assert "does not begin with 0 or 1" in str(inspected.rejection_reason)


class TestAadhaarFormatCheck:
    def test_a_valid_number_passes(self):
        # Act
        check = AadhaarFormatCheck.build(
            document_id="document_1",
            field_key="aadhaarNo",
            aadhaar_number="731655204821",
        )

        # Assert
        assert check.status == CheckStatus.PASS.value
        assert check.check_id == "document_1:aadhaar-format"
        assert check.field_key == "aadhaarNo"

    def test_a_malformed_number_fails_and_carries_the_reason(self):
        # Act
        check = AadhaarFormatCheck.build(
            document_id="document_1", field_key="aadhaarNo", aadhaar_number="123"
        )

        # Assert
        assert check.status == CheckStatus.FAIL.value
        assert "twelve digits" in check.detail

    def test_the_number_is_never_written_into_the_detail(self):
        # Arrange — the detail is copied verbatim into the scrutiny note
        aadhaar_number = "731655204821"

        # Act
        check = AadhaarFormatCheck.build(
            document_id="document_1",
            field_key="aadhaarNo",
            aadhaar_number=aadhaar_number,
        )

        # Assert
        assert aadhaar_number not in check.detail
        assert aadhaar_number not in check.title


class TestAadhaarChecksumEnforcement:
    # A Verhoeff-valid specimen number and its one-digit tamper.
    VALID_NUMBER = "234567890124"
    INVALID_NUMBER = "234567890125"

    def test_checksum_is_off_by_default_so_legacy_numbers_still_pass(self):
        # Arrange — the seeded numbers fail Verhoeff on purpose (ADR-009); with the
        # checksum off they must still read as valid
        # Act
        inspected = AadhaarFormat.inspect(aadhaar_number="731655204821")

        # Assert
        assert inspected.state == AadhaarFormatState.RECOGNISED.value

    def test_a_valid_checksum_passes_when_enforced(self):
        # Act
        inspected = AadhaarFormat.inspect(
            aadhaar_number=self.VALID_NUMBER, verify_checksum=True
        )

        # Assert
        assert inspected.state == AadhaarFormatState.RECOGNISED.value

    def test_a_failing_checksum_is_caught_only_when_enforced(self):
        # Act — the same number reads valid structurally, fails only on the checksum
        without = AadhaarFormat.inspect(aadhaar_number=self.INVALID_NUMBER)
        with_checksum = AadhaarFormat.inspect(
            aadhaar_number=self.INVALID_NUMBER, verify_checksum=True
        )

        # Assert
        assert without.state == AadhaarFormatState.RECOGNISED.value
        assert with_checksum.state == AadhaarFormatState.CHECKSUM_FAILED.value
        assert "check digit does not verify" in str(with_checksum.rejection_reason)

    def test_the_check_fails_on_a_bad_checksum_when_enforced(self):
        # Act
        check = AadhaarFormatCheck.build(
            document_id="document_1",
            field_key="aadhaarNo",
            aadhaar_number=self.INVALID_NUMBER,
            enforce_checksum=True,
        )

        # Assert
        assert check.status == CheckStatus.FAIL.value
        assert "checksum" in check.title.lower()
        assert self.INVALID_NUMBER not in check.detail
