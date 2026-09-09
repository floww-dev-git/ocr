import enum


class CheckStatus(enum.Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    INFO = "info"
    PENDING = "pending"
    UNAVAILABLE = "unavailable"


class CheckGroup(enum.Enum):
    RULE = "rule"
    STRUCTURE = "structure"
    CROSS = "cross"
    EXTERNAL = "external"


class DocumentStage(enum.Enum):
    QUEUED = "queued"
    IDENTIFYING = "identifying"
    EXTRACTING = "extracting"
    CHECKING = "checking"
    VERIFYING = "verifying"
    DONE = "done"


class DocumentStatus(enum.Enum):
    CHECKING = "checking"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"
    ATTENTION = "attention"
    VERIFIED = "verified"


class ThreadStatus(enum.Enum):
    NEW = "new"
    RUNNING = "running"
    ATTENTION = "attention"
    CLEAR = "clear"


class CheckResolution(enum.Enum):
    ACKNOWLEDGED = "acknowledged"
    MANUAL = "manual"
    REQUESTED = "requested"
