import re
from typing import Optional, Set

from document_scrutiny.constants.address_constants import (
    MINIMUM_ADDRESS_TOKEN_LENGTH,
)

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9 ]")
_REPEATED_WHITESPACE = re.compile(r"\s+")


class AddressOverlap:
    """How much of the shorter address the two share.

    Deliberately not a similarity score. An address on a document and an address
    on a form are written to different conventions — "H.No 3-45" against "House
    No. 3/45", one carrying a district the other omits — so what matters is how
    much they agree on, measured against the shorter of the two rather than the
    union. Single characters are dropped because a stray "a" or a broken-off
    house-number fragment is noise, not agreement.
    """

    @classmethod
    def calculate(
        cls, address: Optional[str], comparison_address: Optional[str]
    ) -> float:
        tokens = cls._tokenise(address)
        comparison_tokens = cls._tokenise(comparison_address)
        if not tokens or not comparison_tokens:
            return 0.0
        shared = len(tokens & comparison_tokens)
        return shared / min(len(tokens), len(comparison_tokens))

    @staticmethod
    def _tokenise(address: Optional[str]) -> Set[str]:
        lowered = str(address or "").lower()
        alphanumeric = _NON_ALPHANUMERIC.sub(" ", lowered)
        collapsed = _REPEATED_WHITESPACE.sub(" ", alphanumeric).strip()
        return {
            token
            for token in collapsed.split(" ")
            if len(token) >= MINIMUM_ADDRESS_TOKEN_LENGTH
        }
