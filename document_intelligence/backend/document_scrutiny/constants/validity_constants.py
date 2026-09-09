import enum

# Half a year. Far enough ahead that an officer can ask for a renewal before
# sanction, which is the whole point of warning rather than passing silently.
EXPIRING_SOON_DAYS = 180

VALIDITY_CHECK_KEY = "validity"


class ValidityState(enum.Enum):
    LAPSED = "lapsed"
    EXPIRING_SOON = "expiring_soon"
    VALID = "valid"
    UNREADABLE = "unreadable"
