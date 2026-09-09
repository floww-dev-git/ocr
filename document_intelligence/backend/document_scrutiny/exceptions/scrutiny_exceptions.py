from common.exceptions.base import BaseExceptionClass


class ScrutinyThreadNotFound(BaseExceptionClass):
    def __init__(self, thread_id: str):
        self.thread_id = thread_id


class DocumentNotFound(BaseExceptionClass):
    def __init__(self, thread_id: str, document_id: str):
        self.thread_id = thread_id
        self.document_id = document_id


class UploadRejected(BaseExceptionClass):
    def __init__(self, filename: str, reason: str, message: str):
        self.filename = filename
        self.reason = reason
        self.message = message


class DocumentFieldNotFound(BaseExceptionClass):
    def __init__(self, document_id: str, field_key: str):
        self.document_id = document_id
        self.field_key = field_key


class CheckNotFound(BaseExceptionClass):
    def __init__(self, thread_id: str, check_id: str):
        self.thread_id = thread_id
        self.check_id = check_id


class CheckNotRetryable(BaseExceptionClass):
    def __init__(self, check_id: str, status: str):
        self.check_id = check_id
        self.status = status


class UnknownCheckResolution(BaseExceptionClass):
    def __init__(self, action: str):
        self.action = action


class IssuerCheckMissing(BaseExceptionClass):
    def __init__(self, document_id: str):
        self.document_id = document_id


class NoIssuerToRetry(BaseExceptionClass):
    """Raised for a document type whose department publishes no interface.

    Distinct from `CheckNotRetryable`, which is a department that answered and
    agreed: here nothing was ever asked, and asking again is not the remedy.
    """

    def __init__(self, document_id: str):
        self.document_id = document_id


class NothingToConfirm(BaseExceptionClass):
    def __init__(self, document_id: str):
        self.document_id = document_id


class DocumentBusy(BaseExceptionClass):
    def __init__(self, document_id: str, stage: str):
        self.document_id = document_id
        self.stage = stage
