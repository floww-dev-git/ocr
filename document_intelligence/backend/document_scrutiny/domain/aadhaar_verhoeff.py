"""The Verhoeff checksum an Aadhaar number actually carries.

An Aadhaar number is eleven digits plus a twelfth Verhoeff check digit computed over
the first eleven. The algorithm is the standard dihedral-group Verhoeff scheme: a
multiplication table `d`, a permutation table `p` applied by position, and an inverse
table `inv`. It catches every single-digit error and most adjacent transpositions,
which is why UIDAI uses it.

Pure functions over a string of digits, no Django, so both the specimen generator
and the format check share exactly one implementation and can never disagree about
what "valid" means.
"""
from typing import List

# Multiplication table for the dihedral group D5.
_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

# Permutation table applied to each digit by its position.
_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)

# Inverse table.
_INV = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)


def _digits(number: str) -> List[int]:
    return [int(character) for character in number]


def _checksum(digits: List[int]) -> int:
    """The Verhoeff checksum over the digits read right to left.

    Zero means the sequence (which must already include its check digit) is valid.
    """
    check = 0
    for position, digit in enumerate(reversed(digits)):
        check = _D[check][_P[position % 8][digit]]
    return check


def is_verhoeff_valid(number: str) -> bool:
    """Whether a complete number's trailing Verhoeff check digit is correct."""
    stripped = "".join(str(number or "").split())
    if not stripped.isdigit():
        return False
    return _checksum(_digits(stripped)) == 0


def append_verhoeff_check_digit(stem: str) -> str:
    """Return the stem plus the check digit that makes it Verhoeff-valid.

    The check digit is the inverse of the checksum computed over the stem with a
    placeholder zero in the check position.
    """
    stripped = "".join(str(stem or "").split())
    if not stripped.isdigit():
        raise ValueError("A Verhoeff stem must be digits only.")
    check = 0
    for position, digit in enumerate(reversed(_digits(stripped))):
        # Position 0 is the (not-yet-present) check digit, so the stem starts at 1.
        check = _D[check][_P[(position + 1) % 8][digit]]
    return stripped + str(_INV[check])
