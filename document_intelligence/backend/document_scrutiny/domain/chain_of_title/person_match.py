from typing import Sequence, Tuple

from rapidfuzz import fuzz, utils

from document_extraction.dtos.deed_record_dtos import PartyDTO
from document_scrutiny.constants.chain_constants import (
    ADDRESS_CORROBORATION_SCORE,
    RELATIVE_NAME_CORROBORATION_SCORE,
)

# Lowercases and strips punctuation ("M/S", "&"), so case and formatting never block
# a match that a reader would make without hesitating.
_PROCESS = utils.default_process


class PersonMatch:
    """How alike two sides of a transfer are, and whether anything corroborates it.

    Carried from sale_deed_poc/build/poc/chain.py. Scoring on the name alone and
    taking the higher of two ratios is the part that earns its keep:

    - token_sort_ratio catches a transliteration ('Lakshmi' against 'Laxmi'), which
      must read as a caveat rather than a different person;
    - token_set_ratio catches a buyer's whole name sitting inside a multi-party
      seller string ('Arun Menon' inside 'Zenith Traders, Arun Menon'), which would
      otherwise read as no continuity at all.
    """

    @classmethod
    def best(
        cls, parties: Sequence[PartyDTO], comparison_parties: Sequence[PartyDTO]
    ) -> Tuple[float, bool]:
        best_score = 0.0
        corroborated = False
        for party in parties:
            for comparison_party in comparison_parties:
                score = cls.score_names(
                    name=party.name, comparison_name=comparison_party.name
                )
                if score > best_score:
                    best_score = score
                    corroborated = cls._corroborates(
                        party=party, comparison_party=comparison_party
                    )
        return best_score, corroborated

    @staticmethod
    def score_names(name: str, comparison_name: str) -> float:
        left = name or ""
        right = comparison_name or ""
        return max(
            fuzz.token_sort_ratio(left, right, processor=_PROCESS),
            fuzz.token_set_ratio(left, right, processor=_PROCESS),
        )

    @classmethod
    def _corroborates(cls, party: PartyDTO, comparison_party: PartyDTO) -> bool:
        """A father's name or an address agreeing is what tells two people apart when
        their own names are only nearly the same."""
        return cls._relatives_agree(party, comparison_party) or cls._addresses_agree(
            party, comparison_party
        )

    @staticmethod
    def _relatives_agree(party: PartyDTO, comparison_party: PartyDTO) -> bool:
        if not party.relative_name or not comparison_party.relative_name:
            return False
        return (
            fuzz.token_sort_ratio(
                party.relative_name,
                comparison_party.relative_name,
                processor=_PROCESS,
            )
            >= RELATIVE_NAME_CORROBORATION_SCORE
        )

    @staticmethod
    def _addresses_agree(party: PartyDTO, comparison_party: PartyDTO) -> bool:
        if not party.address or not comparison_party.address:
            return False
        return (
            fuzz.partial_ratio(
                party.address, comparison_party.address, processor=_PROCESS
            )
            >= ADDRESS_CORROBORATION_SCORE
        )
