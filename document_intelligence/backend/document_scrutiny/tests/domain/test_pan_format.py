import pytest

from document_scrutiny.constants.pan_holder_types import (
    HOLDER_TYPE_LABELS_BY_CODE,
    PanFormatState,
)
from document_scrutiny.domain.pan_format import (
    BLANK_PAN_REASON,
    PATTERN_REASON,
    PanFormat,
)

INDIVIDUAL_PAN = "DQRPK4831L"


class TestPanFormat:
    @pytest.mark.parametrize("blank_pan", ["", "   ", None])
    def test_a_blank_pan_is_malformed(self, blank_pan):
        # Arrange — AC4: a PAN that cannot be read has no structure to judge
        # Act
        pan_format = PanFormat.inspect(pan=blank_pan)

        # Assert
        assert pan_format.state == PanFormatState.MALFORMED.value
        assert pan_format.holder_type_code is None
        assert pan_format.holder_type_label is None
        assert pan_format.rejection_reason == BLANK_PAN_REASON

    @pytest.mark.parametrize(
        "wrong_length_pan, expected_length",
        [("DQRPK4831", 9), ("DQRPK4831LM", 11), ("D", 1), ("DQRPK 4831", 10)],
    )
    def test_a_pan_of_the_wrong_length_is_malformed(self, wrong_length_pan, expected_length):
        # Arrange — AC4; the last case is the right length but the wrong shape
        # Act
        pan_format = PanFormat.inspect(pan=wrong_length_pan)

        # Assert
        assert pan_format.state == PanFormatState.MALFORMED.value
        assert pan_format.holder_type_code is None
        assert pan_format.holder_type_label is None
        if expected_length == len(INDIVIDUAL_PAN):
            assert pan_format.rejection_reason == PATTERN_REASON
        else:
            assert pan_format.rejection_reason == (
                f"A PAN is 10 characters; this one reads {expected_length}."
            )

    @pytest.mark.parametrize(
        "malformed_pan",
        [
            "DQR9K4831L",
            "9QRPK4831L",
            "DQRPKA831L",
            "DQRPK483AL",
            "DQRPK48311",
            "dqrpk4831l",
            "DQRPK4831l",
            "DQRPK-831L",
        ],
    )
    def test_a_pan_that_breaks_the_letter_digit_pattern_is_malformed(self, malformed_pan):
        # Arrange — AC4
        # Act
        pan_format = PanFormat.inspect(pan=malformed_pan)

        # Assert
        assert pan_format.state == PanFormatState.MALFORMED.value
        assert pan_format.holder_type_code is None
        assert pan_format.holder_type_label is None
        assert pan_format.rejection_reason == PATTERN_REASON

    def test_a_trailing_newline_is_stripped_like_any_other_whitespace(self):
        # Arrange
        # Act
        pan_format = PanFormat.inspect(pan="DQRPK4831L\n")

        # Assert
        assert pan_format.state == PanFormatState.RECOGNISED.value

    def test_a_well_shaped_pan_with_an_unrecognised_holder_type_is_its_own_state(self):
        # Arrange — the shape is right, so this is not a malformed read
        # Act
        pan_format = PanFormat.inspect(pan="DQRZK4831L")

        # Assert
        assert pan_format.state == PanFormatState.UNRECOGNISED_HOLDER_TYPE.value
        assert pan_format.holder_type_code == "Z"
        assert pan_format.holder_type_label is None
        assert pan_format.rejection_reason is None

    def test_an_individual_pan_is_recognised_and_reads_its_holder_type(self):
        # Arrange
        # Act
        pan_format = PanFormat.inspect(pan=INDIVIDUAL_PAN)

        # Assert
        assert pan_format.state == PanFormatState.RECOGNISED.value
        assert pan_format.holder_type_code == "P"
        assert pan_format.holder_type_label == "Individual"
        assert pan_format.rejection_reason is None

    def test_surrounding_whitespace_is_tolerated(self):
        # Arrange
        # Act
        pan_format = PanFormat.inspect(pan=f"  {INDIVIDUAL_PAN}  ")

        # Assert
        assert pan_format.state == PanFormatState.RECOGNISED.value
        assert pan_format.holder_type_label == "Individual"

    @pytest.mark.parametrize("holder_type_code", sorted(HOLDER_TYPE_LABELS_BY_CODE))
    def test_reads_every_declared_holder_type_code(self, holder_type_code):
        # Arrange
        pan = f"ABC{holder_type_code}D1234E"

        # Act
        pan_format = PanFormat.inspect(pan=pan)

        # Assert
        assert pan_format.state == PanFormatState.RECOGNISED.value
        assert pan_format.holder_type_code == holder_type_code
        assert pan_format.holder_type_label == HOLDER_TYPE_LABELS_BY_CODE[holder_type_code]

    @pytest.mark.parametrize("seeded_pan", ["DQRPK4831L", "AKLPD2291Q", "BNMPS7720K"])
    def test_every_seeded_application_pan_is_a_recognised_individual_pan(self, seeded_pan):
        # Arrange — AC1: the seeded applications all carry valid individual PANs
        # Act
        pan_format = PanFormat.inspect(pan=seeded_pan)

        # Assert
        assert pan_format.state == PanFormatState.RECOGNISED.value
        assert pan_format.holder_type_label == "Individual"
