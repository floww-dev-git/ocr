import enum

BYTES_PER_MEGABYTE = 1024 * 1024
STORED_NAME_LENGTH = 16
DEFAULT_SERVICE_OVERRIDE = "auto"


class UploadRejectionReason(enum.Enum):
    UNSUPPORTED_FORMAT = "unsupported_format"
    TOO_LARGE = "too_large"
    EMPTY_FILE = "empty_file"
