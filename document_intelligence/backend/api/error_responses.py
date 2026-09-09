from typing import Any, Dict, Optional, Tuple

from django.http import JsonResponse

from document_catalog.exceptions.catalog_exceptions import (
    ApplicationNotFound,
    DocumentTypeNotFound,
)
from document_scrutiny.exceptions.scrutiny_exceptions import (
    CheckNotFound,
    CheckNotRetryable,
    DocumentBusy,
    DocumentFieldNotFound,
    DocumentNotFound,
    IssuerCheckMissing,
    NoIssuerToRetry,
    NothingToConfirm,
    ScrutinyThreadNotFound,
    UnknownCheckResolution,
    UploadRejected,
)

NOT_FOUND_STATUS = 404
BAD_REQUEST_STATUS = 400
CONFLICT_STATUS = 409


def build_error_response(error: Exception) -> Optional[JsonResponse]:
    mapped = _map_error(error)
    if mapped is None:
        return None
    status, payload = mapped
    return JsonResponse(payload, status=status)


def _map_error(error: Exception) -> Optional[Tuple[int, Dict[str, Any]]]:
    if isinstance(error, ScrutinyThreadNotFound):
        return NOT_FOUND_STATUS, {
            "errorCode": "THREAD_NOT_FOUND",
            "threadId": error.thread_id,
        }
    if isinstance(error, DocumentNotFound):
        return NOT_FOUND_STATUS, {
            "errorCode": "DOCUMENT_NOT_FOUND",
            "documentId": error.document_id,
        }
    if isinstance(error, ApplicationNotFound):
        return NOT_FOUND_STATUS, {
            "errorCode": "APPLICATION_NOT_FOUND",
            "applicationId": error.application_id,
        }
    if isinstance(error, DocumentTypeNotFound):
        return NOT_FOUND_STATUS, {
            "errorCode": "DOCUMENT_TYPE_NOT_FOUND",
            "documentTypeId": error.document_type_id,
        }
    if isinstance(error, DocumentFieldNotFound):
        return NOT_FOUND_STATUS, {
            "errorCode": "DOCUMENT_FIELD_NOT_FOUND",
            "fieldKey": error.field_key,
        }
    if isinstance(error, CheckNotFound):
        return NOT_FOUND_STATUS, {
            "errorCode": "CHECK_NOT_FOUND",
            "checkId": error.check_id,
        }
    if isinstance(error, IssuerCheckMissing):
        return NOT_FOUND_STATUS, {
            "errorCode": "ISSUER_CHECK_MISSING",
            "documentId": error.document_id,
        }
    if isinstance(error, UploadRejected):
        return BAD_REQUEST_STATUS, {
            "errorCode": error.reason,
            "filename": error.filename,
            "message": error.message,
        }
    if isinstance(error, CheckNotRetryable):
        return BAD_REQUEST_STATUS, {
            "errorCode": "CHECK_NOT_RETRYABLE",
            "checkId": error.check_id,
            "status": error.status,
        }
    if isinstance(error, NoIssuerToRetry):
        return BAD_REQUEST_STATUS, {
            "errorCode": "NO_ISSUER_TO_RETRY",
            "documentId": error.document_id,
        }
    if isinstance(error, NothingToConfirm):
        return BAD_REQUEST_STATUS, {
            "errorCode": "NOTHING_TO_CONFIRM",
            "documentId": error.document_id,
        }
    if isinstance(error, DocumentBusy):
        return CONFLICT_STATUS, {
            "errorCode": "DOCUMENT_BUSY",
            "documentId": error.document_id,
            "stage": error.stage,
        }
    if isinstance(error, UnknownCheckResolution):
        return BAD_REQUEST_STATUS, {
            "errorCode": "UNKNOWN_CHECK_RESOLUTION",
            "action": error.action,
        }
    return None
