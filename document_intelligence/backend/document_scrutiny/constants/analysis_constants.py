import enum


class AnalysisStep(enum.Enum):
    IDENTIFY = "identify"
    EXTRACT = "extract"
    CHECKS = "checks"
    VERIFY = "verify"


class StepState(enum.Enum):
    RUNNING = "running"
    DONE = "done"


class AnalysisEventType(enum.Enum):
    STEP = "step"
    DOCUMENT = "doc"
    SUMMARY = "summary"
    # Only a thread holding registered deeds gets one. It arrives after the summary,
    # because title can only be traced once every deed in the run has been read.
    CHAIN = "chain"
    ERROR = "error"
    DONE = "done"


UNSUPPORTED_CHECK_KEY = "supported"
UNCLASSIFIED_DOCUMENT_TYPE_ID = "unknown"

UNSUPPORTED_TYPE_MESSAGE = "{label} is recognised but not supported in this build."
UNCLASSIFIED_DOCUMENT_MESSAGE = (
    "We could not tell what {filename} is. Check the scan, or attach a clearer copy."
)
UNREADABLE_DOCUMENT_MESSAGE = (
    "{filename} could not be read. Attach a clearer scan, or enter the details by hand."
)
UNEXPECTED_FAILURE_MESSAGE = (
    "Something went wrong while reading {filename}. Nothing has been recorded against it."
)

ABANDONED_RUN_CHECK_KEY = "run-incomplete"
MAX_ANALYSIS_PASSES = 5
