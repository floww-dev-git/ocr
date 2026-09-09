import pytest

from document_scrutiny.constants.check_thresholds import (
    EXACT_NAME_MATCH,
    NAME_MATCH_WARNING_FLOOR,
)
from document_scrutiny.domain.name_similarity import NameSimilarity

DOCUMENT_NAME_WITH_DROPPED_LETTER = "MOHAMMED IRFAN SIDDIQI"
APPLICATION_NAME = "Mohammed Irfan Siddiqui"
PINNED_SIMILARITY_FOR_DROPPED_LETTER = 0.958


class TestNameSimilarity:
    @pytest.mark.parametrize(
        "name, comparison_name",
        [
            ("", "Mohammed Irfan Siddiqui"),
            ("Mohammed Irfan Siddiqui", ""),
            ("", ""),
            ("   ", "Mohammed Irfan Siddiqui"),
            (".,-", "Mohammed Irfan Siddiqui"),
            (None, "Mohammed Irfan Siddiqui"),
            ("Mohammed Irfan Siddiqui", None),
            (None, "Nona"),
        ],
    )
    def test_a_name_with_no_usable_tokens_scores_zero(self, name, comparison_name):
        # Arrange — a missing name must score zero, not be read as the token
        # "none" and then near-match a real name above the warning floor
        # Act
        similarity = NameSimilarity.calculate(name=name, comparison_name=comparison_name)

        # Assert
        assert similarity == 0

    def test_two_unrelated_names_score_zero(self):
        # Arrange
        name = "Srinivas Rao Kandula"
        comparison_name = "Lakshmi Prasanna Devarakonda"

        # Act
        similarity = NameSimilarity.calculate(name=name, comparison_name=comparison_name)

        # Assert
        assert similarity == 0

    def test_a_token_below_the_seventy_five_percent_floor_contributes_nothing(self):
        # Arrange — "rao" against "ram" is one edit over three characters, 0.667
        # Act
        similarity = NameSimilarity.calculate(name="Rao", comparison_name="Ram")

        # Assert
        assert similarity == 0

    def test_a_matched_comparison_token_is_not_reused_by_a_later_token(self):
        # Arrange — two tokens compete for the single comparison token
        # Act
        similarity = NameSimilarity.calculate(name="Rao Rao", comparison_name="Rao")

        # Assert
        assert similarity == 0.667

    def test_tied_candidates_resolve_to_the_first_of_them(self):
        # Arrange — "ann" scores 0.75 against both "anna" and "anne"; taking the
        # first leaves "anna" to settle for "anne", so the total is lower than
        # an optimal pairing would give.
        # Act
        similarity = NameSimilarity.calculate(name="Ann Anna", comparison_name="Anna Anne")

        # Assert
        assert similarity == 0.75

    def test_an_earlier_token_may_greedily_consume_a_later_tokens_best_match(self):
        # Arrange — the initial "K" matches "Kandula" outright, so the real
        # surname is left with only "Rao" and scores nothing.
        # Act
        similarity = NameSimilarity.calculate(
            name="Srinivas K Kandula", comparison_name="Srinivas Rao Kandula"
        )

        # Assert
        assert similarity == 0.667

    def test_the_score_is_not_symmetric_when_a_tie_is_broken_differently(self):
        # Arrange
        name = "Ann Anna"
        comparison_name = "Anna Anne"

        # Act
        forward = NameSimilarity.calculate(name=name, comparison_name=comparison_name)
        reversed_order = NameSimilarity.calculate(
            name=comparison_name, comparison_name=name
        )

        # Assert
        assert forward == 0.75
        assert reversed_order == 0.875

    def test_identical_names_score_one(self):
        # Arrange
        name = "Mohammed Irfan Siddiqui"

        # Act
        similarity = NameSimilarity.calculate(name=name, comparison_name=name)

        # Assert
        assert similarity == EXACT_NAME_MATCH

    def test_case_and_punctuation_are_ignored(self):
        # Arrange
        # Act
        similarity = NameSimilarity.calculate(
            name="SRINIVAS RAO KANDULA.", comparison_name="Srinivas  Rao,  Kandula"
        )

        # Assert
        assert similarity == EXACT_NAME_MATCH

    def test_punctuation_between_tokens_separates_them_rather_than_fusing_them(self):
        # Arrange — a hyphen becomes a space, so the two names stay two tokens
        # Act
        similarity = NameSimilarity.calculate(
            name="Srinivas-Rao Kandula", comparison_name="Srinivas Rao Kandula"
        )

        # Assert
        assert similarity == EXACT_NAME_MATCH

    def test_digits_survive_normalisation_as_their_own_token(self):
        # Arrange — normalisation keeps [a-z0-9], so "12" is a comparable token
        # Act
        matching = NameSimilarity.calculate(name="Flat 12", comparison_name="flat 12")
        differing = NameSimilarity.calculate(name="Flat 12", comparison_name="flat 99")

        # Assert
        assert matching == EXACT_NAME_MATCH
        assert differing == 0.5

    def test_a_single_letter_initial_matches_the_full_token_it_abbreviates(self):
        # Arrange
        # Act
        similarity = NameSimilarity.calculate(
            name="Srinivas R Kandula", comparison_name="Srinivas Rao Kandula"
        )

        # Assert
        assert similarity == EXACT_NAME_MATCH

    def test_a_missing_middle_token_lands_above_the_warning_floor(self):
        # Arrange
        # Act
        similarity = NameSimilarity.calculate(
            name="Mohammed Siddiqui", comparison_name="Mohammed Irfan Siddiqui"
        )

        # Assert
        assert similarity == 0.8
        assert NAME_MATCH_WARNING_FLOOR <= similarity < EXACT_NAME_MATCH

    def test_a_score_on_a_half_thousandth_boundary_rounds_up(self):
        # Arrange — three edits over sixteen characters is exactly 0.8125, where
        # half-even rounding would give 0.812 instead of the prototype's 0.813.
        # Act
        similarity = NameSimilarity.calculate(
            name="abcdefghijklmnop", comparison_name="abcdefghijklmxyz"
        )

        # Assert
        assert similarity == 0.813

    def test_the_score_is_quantised_to_three_decimal_places(self):
        # Arrange
        # Act
        similarity = NameSimilarity.calculate(
            name="Mohammed Siddiqui Khan", comparison_name="Mohammed Irfan Siddiqui Khan"
        )

        # Assert
        assert similarity == 0.857

    def test_one_dropped_letter_scores_the_pinned_prototype_value(self):
        # Arrange — AC2: a name differing by one character warns, never passes or fails
        # Act
        similarity = NameSimilarity.calculate(
            name=DOCUMENT_NAME_WITH_DROPPED_LETTER, comparison_name=APPLICATION_NAME
        )

        # Assert
        assert similarity == PINNED_SIMILARITY_FOR_DROPPED_LETTER
        assert NAME_MATCH_WARNING_FLOOR <= similarity < EXACT_NAME_MATCH

    @pytest.mark.parametrize(
        "document_name, application_name",
        [
            ("SRINIVAS RAO KANDULA", "Srinivas Rao Kandula"),
            ("VENKATESWARA RAO KANDULA", "Venkateswara Rao Kandula"),
            ("LAKSHMI PRASANNA DEVARAKONDA", "Lakshmi Prasanna Devarakonda"),
            ("RAMESH BABU DEVARAKONDA", "Ramesh Babu Devarakonda"),
            ("MOHAMMED YOUSUF SIDDIQUI", "Mohammed Yousuf Siddiqui"),
        ],
    )
    def test_the_clean_seeded_applications_score_a_full_match(
        self, document_name, application_name
    ):
        # Arrange — AC1: every field of a clean application agrees
        # Act
        similarity = NameSimilarity.calculate(
            name=document_name, comparison_name=application_name
        )

        # Assert
        assert similarity == EXACT_NAME_MATCH
