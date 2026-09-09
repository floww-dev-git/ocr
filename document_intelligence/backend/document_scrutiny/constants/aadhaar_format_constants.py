import enum

AADHAAR_LENGTH = 12
# Spelled out because it is read by an officer, not parsed.
AADHAAR_LENGTH_IN_WORDS = "twelve"
# UIDAI never issues a number opening with 0 or 1, which keeps an Aadhaar
# distinguishable from a bank or ration-card number of the same length.
DISALLOWED_LEADING_DIGITS = ("0", "1")


class AadhaarFormatState(enum.Enum):
    MALFORMED = "malformed"
    # Twelve digits with a valid leading digit, but the trailing Verhoeff check
    # digit does not verify — so it is a well-shaped number that no genuine Aadhaar
    # could carry. Only reached when checksum enforcement is asked for.
    CHECKSUM_FAILED = "checksum_failed"
    RECOGNISED = "recognised"


CHECKSUM_FAILED_REASON = (
    "The twelve digits are shaped like an Aadhaar but the check digit does not "
    "verify, so this is not a genuine Aadhaar number."
)
