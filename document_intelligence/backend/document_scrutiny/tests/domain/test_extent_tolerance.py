import pytest

from document_scrutiny.constants.extent_constants import EXTENT_TOLERANCE_SQ_YARD
from document_scrutiny.domain.comparison_rules.extent_tolerance import ExtentTolerance


class TestReadExtent:
    @pytest.mark.parametrize(
        "written,expected",
        [
            ("267 sq. yds", 267.0),
            ("267", 267.0),
            ("400 Sq. Yards (334.45 Sq. Metres)", 400.0),
            ("1,200 sq. yds", 1200.0),
            ("183.5 sq yd", 183.5),
            ("Admeasuring 420 square yards", 420.0),
        ],
    )
    def test_the_leading_number_is_what_carries_the_meaning(self, written, expected):
        # Act
        read = ExtentTolerance.read_extent(written)

        # Assert
        assert read == expected

    @pytest.mark.parametrize("written", [None, "", "   ", "not stated", "sq. yds"])
    def test_an_extent_with_no_number_reads_as_nothing(self, written):
        # Act
        read = ExtentTolerance.read_extent(written)

        # Assert
        assert read is None


class TestExtentsAgree:
    def test_the_same_extent_written_two_ways_agrees(self):
        # Act
        agree = ExtentTolerance.agree(
            extent="267 sq. yds",
            comparison_extent="267",
            tolerance=EXTENT_TOLERANCE_SQ_YARD,
        )

        # Assert
        assert agree is True

    def test_a_rounding_difference_agrees(self):
        # Arrange — conversions between yards, metres and feet round
        # Act
        agree = ExtentTolerance.agree(
            extent="267.2 sq. yds",
            comparison_extent="267",
            tolerance=EXTENT_TOLERANCE_SQ_YARD,
        )

        # Assert
        assert agree is True

    def test_a_difference_of_one_yard_does_not_agree(self):
        # Act
        agree = ExtentTolerance.agree(
            extent="268 sq. yds",
            comparison_extent="267",
            tolerance=EXTENT_TOLERANCE_SQ_YARD,
        )

        # Assert
        assert agree is False

    def test_exactly_on_the_tolerance_does_not_agree(self):
        # Act
        agree = ExtentTolerance.agree(
            extent="267.5", comparison_extent="267", tolerance=EXTENT_TOLERANCE_SQ_YARD
        )

        # Assert
        assert agree is False

    def test_the_extra_extent_of_an_over_conveyance_does_not_agree(self):
        # Arrange — 600 sold against 400 acquired is the POC's gap scenario
        # Act
        agree = ExtentTolerance.agree(
            extent="600 Sq. Yards",
            comparison_extent="400 Sq. Yards",
            tolerance=EXTENT_TOLERANCE_SQ_YARD,
        )

        # Assert
        assert agree is False

    @pytest.mark.parametrize(
        "extent,comparison_extent",
        [(None, "267"), ("267", None), ("not stated", "267"), ("267", "")],
    )
    def test_an_extent_that_could_not_be_read_does_not_agree_with_anything(
        self, extent, comparison_extent
    ):
        # Arrange — reading a missing extent as agreement would pass an unchecked plot
        # Act
        agree = ExtentTolerance.agree(
            extent=extent,
            comparison_extent=comparison_extent,
            tolerance=EXTENT_TOLERANCE_SQ_YARD,
        )

        # Assert
        assert agree is False
