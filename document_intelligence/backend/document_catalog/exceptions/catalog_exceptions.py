from common.exceptions.base import BaseExceptionClass


class DocumentTypeNotFound(BaseExceptionClass):
    def __init__(self, document_type_id: str):
        self.document_type_id = document_type_id


class IssuerServiceNotFound(BaseExceptionClass):
    def __init__(self, issuer_service_id: str):
        self.issuer_service_id = issuer_service_id


class ApplicationNotFound(BaseExceptionClass):
    def __init__(self, application_id: str):
        self.application_id = application_id
