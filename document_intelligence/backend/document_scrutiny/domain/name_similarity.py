import re
from typing import List, Optional, Set, Tuple

from common.rounding import round_half_up
from document_scrutiny.constants.name_similarity_constants import (
    MINIMUM_TOKEN_SIMILARITY,
    SIMILARITY_DECIMAL_PLACES,
)

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9 ]")
_REPEATED_WHITESPACE = re.compile(r"\s+")


class NameSimilarity:
    @classmethod
    def calculate(cls, name: Optional[str], comparison_name: Optional[str]) -> float:
        tokens = cls._tokenise(name)
        comparison_tokens = cls._tokenise(comparison_name)
        if not tokens or not comparison_tokens:
            return 0.0

        matched_total = cls._sum_best_token_matches(
            tokens=tokens, comparison_tokens=comparison_tokens
        )
        token_count = len(tokens) + len(comparison_tokens)
        return cls._quantise(2 * matched_total / token_count)

    @classmethod
    def _sum_best_token_matches(
        cls, tokens: List[str], comparison_tokens: List[str]
    ) -> float:
        matched_indexes: Set[int] = set()
        matched_total = 0.0
        for token in tokens:
            best_similarity, best_index = cls._find_best_match(
                token=token,
                comparison_tokens=comparison_tokens,
                matched_indexes=matched_indexes,
            )
            if best_index is None:
                continue
            matched_indexes.add(best_index)
            matched_total += best_similarity
        return matched_total

    @classmethod
    def _find_best_match(
        cls, token: str, comparison_tokens: List[str], matched_indexes: Set[int]
    ) -> Tuple[float, Optional[int]]:
        best_similarity = 0.0
        best_index: Optional[int] = None
        for index, comparison_token in enumerate(comparison_tokens):
            if index in matched_indexes:
                continue
            similarity = cls._token_similarity(token=token, comparison_token=comparison_token)
            if similarity > best_similarity:
                best_similarity = similarity
                best_index = index
        return best_similarity, best_index

    @classmethod
    def _token_similarity(cls, token: str, comparison_token: str) -> float:
        if token == comparison_token:
            return 1.0
        if cls._abbreviates(initial=token, full_token=comparison_token):
            return 1.0
        if cls._abbreviates(initial=comparison_token, full_token=token):
            return 1.0

        longest_length = max(len(token), len(comparison_token))
        distance = cls._edit_distance(token=token, comparison_token=comparison_token)
        similarity = 1 - distance / longest_length
        if similarity < MINIMUM_TOKEN_SIMILARITY:
            return 0.0
        return similarity

    @staticmethod
    def _abbreviates(initial: str, full_token: str) -> bool:
        return len(initial) == 1 and full_token.startswith(initial)

    @staticmethod
    def _edit_distance(token: str, comparison_token: str) -> int:
        previous_row = list(range(len(comparison_token) + 1))
        for token_index, token_character in enumerate(token, start=1):
            current_row = [token_index]
            for comparison_index, comparison_character in enumerate(comparison_token, start=1):
                substitution_cost = int(token_character != comparison_character)
                current_row.append(
                    min(
                        previous_row[comparison_index] + 1,
                        current_row[comparison_index - 1] + 1,
                        previous_row[comparison_index - 1] + substitution_cost,
                    )
                )
            previous_row = current_row
        return previous_row[-1]

    @staticmethod
    def _tokenise(name: Optional[str]) -> List[str]:
        lowered = str(name or "").lower()
        alphanumeric = _NON_ALPHANUMERIC.sub(" ", lowered)
        collapsed = _REPEATED_WHITESPACE.sub(" ", alphanumeric).strip()
        return [token for token in collapsed.split(" ") if token]

    @staticmethod
    def _quantise(similarity: float) -> float:
        return round_half_up(similarity, SIMILARITY_DECIMAL_PLACES)
