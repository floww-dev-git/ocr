import enum

DEMO_OUTCOME_HEADER = "X-Demo-Outcome"
API_KEY_HEADER = "X-Api-Key"

BAD_REQUEST_STATUS = 400
UNAUTHORISED_STATUS = 401
SERVICE_UNAVAILABLE_STATUS = 503


class DemoOutcome(enum.Enum):
    """What the officer forced this department to do, from the Demo menu.

    Shared by every mocked issuer: the demo lever has to behave the same way
    whichever department it is pulled on.
    """

    AUTO = "auto"
    PASS = "pass"
    FAIL = "fail"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
