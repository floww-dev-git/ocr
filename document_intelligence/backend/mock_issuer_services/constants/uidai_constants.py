import enum

TRANSACTION_ID_PREFIX = "UID"
TRANSACTION_ID_LENGTH = 10


class UidaiAuthStatus(enum.Enum):
    # UIDAI's demographic authentication answers Y or N rather than a word.
    MATCHED = "Y"
    NOT_MATCHED = "N"
    NOT_FOUND = "NOT_FOUND"


class UidaiDemographicField(enum.Enum):
    NAME = "name"
    DATE_OF_BIRTH = "dob"
    GENDER = "gender"


class UidaiFailureReason(enum.Enum):
    NO_SUCH_AADHAAR = "NO_SUCH_AADHAAR"
    DEMOGRAPHIC_MISMATCH = "DEMOGRAPHIC_MISMATCH"


class UidaiRequestError(enum.Enum):
    API_KEY_REQUIRED = "API_KEY_REQUIRED"
    API_KEY_INVALID = "API_KEY_INVALID"
    INVALID_REQUEST_BODY = "INVALID_REQUEST_BODY"
    AADHAAR_REQUIRED = "AADHAAR_REQUIRED"
    AADHAAR_MALFORMED = "AADHAAR_MALFORMED"
    NAME_REQUIRED = "NAME_REQUIRED"
    UNKNOWN_DEMO_OUTCOME = "UNKNOWN_DEMO_OUTCOME"
    DEMO_OUTCOME_NOT_PERMITTED = "DEMO_OUTCOME_NOT_PERMITTED"


class UidaiServerError(enum.Enum):
    AUTH_SERVER_UNAVAILABLE = "AUTH_SERVER_UNAVAILABLE"
