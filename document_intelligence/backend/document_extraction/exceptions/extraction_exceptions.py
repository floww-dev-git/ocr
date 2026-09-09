from common.exceptions.base import BaseExceptionClass


class NoSampleReadForApplication(BaseExceptionClass):
    def __init__(self, application_id: str, document_type_id: str = ""):
        self.application_id = application_id
        self.document_type_id = document_type_id


class UnsupportedExtractionMode(BaseExceptionClass):
    def __init__(self, extraction_mode: str):
        self.extraction_mode = extraction_mode


class DocumentTypeNotSupported(BaseExceptionClass):
    def __init__(self, document_type_id: str, document_type_label: str):
        self.document_type_id = document_type_id
        self.document_type_label = document_type_label


class DocumentReadNotRegistered(BaseExceptionClass):
    """A type the catalog calls implemented has no read instructions in this build.

    Deliberately not an `ExtractionFailed`: that one tells the officer the scan
    could not be read and to attach a clearer copy, which would be untrue here and
    would send them off to rescan a perfectly good document. This is a wiring
    mistake and reads as one.
    """

    def __init__(self, document_type_id: str):
        self.document_type_id = document_type_id


class ExtractionFailed(BaseExceptionClass):
    def __init__(self, filename: str, reason: str):
        self.filename = filename
        self.reason = reason


class ExtractionCredentialMissing(BaseExceptionClass):
    def __init__(self, variable_name: str):
        self.variable_name = variable_name
