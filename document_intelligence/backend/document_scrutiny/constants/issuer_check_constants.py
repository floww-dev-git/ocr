import enum
from typing import Mapping

ISSUER_CHECK_KEY = "issuer"


class IssuerAnswerOutcome(enum.Enum):
    CONFIRMED = "confirmed"
    PARTIAL_MATCH = "partial_match"
    NOT_MATCHED = "not_matched"
    NO_RECORD = "no_record"
    UNREACHABLE = "unreachable"


class IssuerUnreachableReason(enum.Enum):
    TIMED_OUT = "timed_out"
    CONNECTION_FAILED = "connection_failed"
    REFUSED_CREDENTIALS = "refused_credentials"
    REJECTED_REQUEST = "rejected_request"
    SERVER_ERROR = "server_error"
    UNREADABLE_ANSWER = "unreadable_answer"


DISAGREEING_FIELD_LABELS: Mapping[str, str] = {
    "name": "the name",
    "dob": "the date of birth",
    "gender": "the gender",
}

RETRY_ADVICE = "Retry, or verify against the original and mark it verified by hand."
