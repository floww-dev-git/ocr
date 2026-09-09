import enum

DEMO_OUTCOME_HEADER = "X-Demo-Outcome"
API_KEY_HEADER = "X-Api-Key"
MILLISECONDS_PER_SECOND = 1000


class ServiceOverride(enum.Enum):
    AUTO = "auto"
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"


class IssuerOutcome(enum.Enum):
    CONFIRMED = "confirmed"
    PARTIAL_MATCH = "partial_match"
    NOT_MATCHED = "not_matched"
    NO_RECORD = "no_record"
    UNREACHABLE = "unreachable"


class IssuerStatus(enum.Enum):
    """How the Income Tax Department reports a PAN verification."""

    VALID = "VALID"
    NOT_MATCHED = "N"
    NOT_FOUND = "NOT_FOUND"


class UidaiStatus(enum.Enum):
    """How UIDAI reports a demographic authentication."""

    MATCHED = "Y"
    NOT_MATCHED = "N"
    NOT_FOUND = "NOT_FOUND"


class SarathiStatus(enum.Enum):
    """How the Transport Department reports a licence lookup."""

    ACTIVE = "ACTIVE"
    NOT_MATCHED = "N"
    NOT_FOUND = "NOT_FOUND"


class IgrsStatus(enum.Enum):
    """How the registrar reports a deed lookup."""

    REGISTERED = "REGISTERED"
    NOT_MATCHED = "N"
    NOT_FOUND = "NOT_FOUND"


class UnreachableReason(enum.Enum):
    TIMED_OUT = "timed_out"
    CONNECTION_FAILED = "connection_failed"
    REFUSED_CREDENTIALS = "refused_credentials"
    REJECTED_REQUEST = "rejected_request"
    SERVER_ERROR = "server_error"
    UNREADABLE_ANSWER = "unreadable_answer"


class DisagreeingField(enum.Enum):
    NAME = "name"
    DATE_OF_BIRTH = "dob"
    GENDER = "gender"


# What UIDAI answers on. Anything absent from its `matched` list is a disagreement,
# so this is the set the reader measures the answer against.
ALL_UIDAI_DEMOGRAPHICS = (
    DisagreeingField.NAME.value,
    DisagreeingField.DATE_OF_BIRTH.value,
    DisagreeingField.GENDER.value,
)
