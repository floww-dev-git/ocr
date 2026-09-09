import pytest

from document_scrutiny.constants.address_constants import ADDRESS_OVERLAP_PASS_FLOOR
from document_scrutiny.domain.comparison_rules.address_overlap import AddressOverlap


class TestAddressOverlap:
    def test_the_same_address_agrees_completely(self):
        # Arrange
        address = "H.No 3-45, Ameenpur, Sangareddy 502032"

        # Act
        overlap = AddressOverlap.calculate(
            address=address, comparison_address=address
        )

        # Assert
        assert overlap == 1.0

    def test_punctuation_and_case_do_not_count_against_agreement(self):
        # Arrange — the same place written to two conventions
        # Act
        overlap = AddressOverlap.calculate(
            address="H.No 3-45, AMEENPUR, Sangareddy 502032",
            comparison_address="h no 3 45 ameenpur sangareddy 502032",
        )

        # Assert
        assert overlap == 1.0

    def test_two_unrelated_addresses_share_nothing(self):
        # Act
        overlap = AddressOverlap.calculate(
            address="Banjara Hills, Hyderabad 500034",
            comparison_address="Ameenpur, Sangareddy 502032",
        )

        # Assert
        assert overlap == 0.0

    def test_the_seeded_moved_applicant_falls_below_the_floor(self):
        # Arrange — the card still carries the previous address (AC: advisory warning)
        # Act
        overlap = AddressOverlap.calculate(
            address="H.No 8-2-293/82, Road No 12, Banjara Hills, Hyderabad 500034",
            comparison_address=(
                "Plot 42, Sri Sai Nagar Colony, Bachupally, Medchal-Malkajgiri 500090"
            ),
        )

        # Assert
        assert overlap < ADDRESS_OVERLAP_PASS_FLOOR

    def test_a_shorter_address_contained_in_a_longer_one_agrees_completely(self):
        # Arrange — a form omitting the district has not contradicted the card, so
        # the shorter address is what the share is measured against
        # Act
        overlap = AddressOverlap.calculate(
            address="Plot 42, Sri Sai Nagar Colony, Bachupally, Medchal-Malkajgiri 500090",
            comparison_address="Sri Sai Nagar Colony Bachupally",
        )

        # Assert
        assert overlap == 1.0

    def test_exactly_half_the_shorter_address_reaches_the_floor(self):
        # Act
        overlap = AddressOverlap.calculate(
            address="alpha beta gamma delta",
            comparison_address="alpha beta epsilon zeta",
        )

        # Assert
        assert overlap == 0.5
        assert overlap >= ADDRESS_OVERLAP_PASS_FLOOR

    def test_just_under_half_falls_below_the_floor(self):
        # Act
        overlap = AddressOverlap.calculate(
            address="alpha beta gamma delta epsilon",
            comparison_address="alpha zeta eta theta iota",
        )

        # Assert
        assert overlap < ADDRESS_OVERLAP_PASS_FLOOR

    def test_single_character_tokens_are_not_treated_as_agreement(self):
        # Arrange — a stray OCR mark shared by both is noise, not a matching address
        # Act
        overlap = AddressOverlap.calculate(
            address="a Banjara Hills", comparison_address="a Ameenpur"
        )

        # Assert
        assert overlap == 0.0

    @pytest.mark.parametrize(
        "address,comparison_address",
        [(None, "Ameenpur"), ("Ameenpur", None), ("", "Ameenpur"), ("   ", "Ameenpur")],
    )
    def test_a_missing_address_agrees_with_nothing_rather_than_everything(
        self, address, comparison_address
    ):
        # Act
        overlap = AddressOverlap.calculate(
            address=address, comparison_address=comparison_address
        )

        # Assert
        assert overlap == 0.0
