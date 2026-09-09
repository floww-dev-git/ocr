import logging

from document_scrutiny.adapters.failure_reporter_interface import (
    FailureReporterInterface,
)

logger = logging.getLogger(__name__)


class LoggingFailureReporter(FailureReporterInterface):
    def report(self, message: str, error: BaseException) -> None:
        logger.error(message, exc_info=error)
