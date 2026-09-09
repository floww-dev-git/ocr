import pytest

from document_scrutiny.domain.aadhaar_verhoeff import (
    append_verhoeff_check_digit,
    is_verhoeff_valid,
)


class TestVerhoeff:
    # Published Verhoeff-valid sequences (the algorithm's own test vectors).
    @pytest.mark.parametrize("number", ["2363", "758722", "123412341234"])
    def test_known_valid_numbers_verify(self, number):
        assert is_verhoeff_valid(number) is True

    def test_a_single_digit_error_is_caught(self):
        # Arrange — Verhoeff's whole point is catching a one-digit slip
        valid = append_verhoeff_check_digit("23456789012")

        # Act — bump one interior digit
        tampered = valid[:3] + str((int(valid[3]) + 1) % 10) + valid[4:]

        # Assert
        assert is_verhoeff_valid(valid) is True
        assert is_verhoeff_valid(tampered) is False

    def test_an_adjacent_transposition_is_caught(self):
        # Arrange
        valid = append_verhoeff_check_digit("23456789012")
        # Act — swap two adjacent, non-equal digits
        chars = list(valid)
        for i in range(len(chars) - 1):
            if chars[i] != chars[i + 1]:
                chars[i], chars[i + 1] = chars[i + 1], chars[i]
                break
        transposed = "".join(chars)

        # Assert
        assert transposed != valid
        assert is_verhoeff_valid(transposed) is False

    def test_append_then_verify_round_trips(self):
        for stem in ["23456789012", "56789012345", "98765432101"]:
            assert is_verhoeff_valid(append_verhoeff_check_digit(stem)) is True

    def test_non_digits_are_not_valid(self):
        assert is_verhoeff_valid("23456789012X") is False
        assert is_verhoeff_valid("") is False

    def test_spaces_are_ignored(self):
        valid = append_verhoeff_check_digit("23456789012")
        spaced = f"{valid[0:4]} {valid[4:8]} {valid[8:12]}"
        assert is_verhoeff_valid(spaced) is True

    def test_a_stem_must_be_digits(self):
        with pytest.raises(ValueError):
            append_verhoeff_check_digit("abc")
