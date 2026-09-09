import uuid
from pathlib import Path
from typing import Mapping

from document_scrutiny.constants.upload_constants import (
    STORED_NAME_LENGTH,
    UploadRejectionReason,
)
from document_scrutiny.dtos.thread_dtos import IncomingFileDTO, UploadLimitsDTO
from document_scrutiny.exceptions.scrutiny_exceptions import UploadRejected

UNKNOWN_FILE_FORMAT = "FILE"

_FORMATS_BY_EXTENSION: Mapping[str, str] = {
    ".pdf": "PDF",
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".tif": "TIFF",
    ".tiff": "TIFF",
}


class UploadGuard:
    @classmethod
    def check(cls, incoming: IncomingFileDTO, limits: UploadLimitsDTO) -> None:
        extension = cls._read_extension(incoming.filename)
        if extension not in limits.allowed_extensions:
            raise UploadRejected(
                filename=incoming.filename,
                reason=UploadRejectionReason.UNSUPPORTED_FORMAT.value,
                message=cls._unsupported_message(extension=extension, limits=limits),
            )
        if not incoming.content:
            raise UploadRejected(
                filename=incoming.filename,
                reason=UploadRejectionReason.EMPTY_FILE.value,
                message="The file is empty. Attach the scan again.",
            )
        if len(incoming.content) > limits.max_bytes:
            raise UploadRejected(
                filename=incoming.filename,
                reason=UploadRejectionReason.TOO_LARGE.value,
                message=cls._too_large_message(
                    size_bytes=len(incoming.content), limits=limits
                ),
            )

    @classmethod
    def read_file_format(cls, filename: str) -> str:
        extension = cls._read_extension(filename)
        return _FORMATS_BY_EXTENSION.get(extension, UNKNOWN_FILE_FORMAT)

    @classmethod
    def build_stored_name(cls, filename: str) -> str:
        # The officer's filename is never used on disk: it may carry a path.
        token = uuid.uuid4().hex[:STORED_NAME_LENGTH]
        return f"{token}{cls._read_extension(filename)}"

    @staticmethod
    def _read_extension(filename: str) -> str:
        return Path(str(filename or "")).suffix.lower()

    @staticmethod
    def _unsupported_message(extension: str, limits: UploadLimitsDTO) -> str:
        readable = ", ".join(limits.allowed_extensions)
        named = extension or "no extension"
        return f"This build reads {readable}; the file has {named}."

    @staticmethod
    def _too_large_message(size_bytes: int, limits: UploadLimitsDTO) -> str:
        return f"The file is {size_bytes} bytes; the limit is {limits.max_bytes} bytes."
