import enum
from typing import Mapping

LETTER_PREFIX_LENGTH = 5
DIGIT_BLOCK_LENGTH = 4
LETTER_SUFFIX_LENGTH = 1
PAN_LENGTH = LETTER_PREFIX_LENGTH + DIGIT_BLOCK_LENGTH + LETTER_SUFFIX_LENGTH
HOLDER_TYPE_POSITION = 3

HOLDER_TYPE_LABELS_BY_CODE: Mapping[str, str] = {
    "P": "Individual",
    "C": "Company",
    "H": "Hindu undivided family",
    "F": "Firm or limited liability partnership",
    "A": "Association of persons",
    "B": "Body of individuals",
    "T": "Trust",
    "L": "Local authority",
    "J": "Artificial juridical person",
    "G": "Government agency",
}


class PanFormatState(enum.Enum):
    MALFORMED = "malformed"
    UNRECOGNISED_HOLDER_TYPE = "unrecognised_holder_type"
    RECOGNISED = "recognised"
