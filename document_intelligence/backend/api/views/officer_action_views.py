from typing import Any, Dict, Optional, Tuple

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from api.error_responses import BAD_REQUEST_STATUS
from api.interactor_factory import (
    build_confirm_document_fields_interactor,
    build_get_scrutiny_note_interactor,
    build_resolve_check_interactor,
    build_retry_issuer_verification_interactor,
    build_update_document_field_interactor,
    build_update_service_overrides_interactor,
)
from api.request_handling import read_json_body, translate_domain_errors
from document_scrutiny.dtos.note_dtos import ScrutinyNoteRequestDTO
from document_scrutiny.dtos.officer_action_dtos import (
    ConfirmDocumentFieldsRequestDTO,
    ResolveCheckRequestDTO,
    RetryIssuerVerificationRequestDTO,
    UpdateDocumentFieldRequestDTO,
    UpdateServiceOverridesRequestDTO,
)
from document_scrutiny.presenters.document_presenter import DocumentPresenter

VALUE_KEY = "value"
ACTION_KEY = "action"
SERVICE_OVERRIDES_KEY = "serviceOverrides"
MAX_FIELD_VALUE_LENGTH = 256


@csrf_exempt
@require_http_methods(["PATCH"])
@translate_domain_errors
def update_document_field(
    request: HttpRequest, thread_id: str, document_id: str, field_key: str
) -> JsonResponse:
    payload, error = read_json_body(request)
    if error is not None:
        return error
    value, error = _read_field_value(payload)
    if error is not None:
        return error

    change = build_update_document_field_interactor().update_field(
        request=UpdateDocumentFieldRequestDTO(
            thread_id=thread_id,
            document_id=document_id,
            field_key=field_key,
            value=value,
        )
    )
    return JsonResponse(DocumentPresenter.get_document_change_response(change=change))


def _read_field_value(
    payload: Dict[str, Any],
) -> Tuple[str, Optional[JsonResponse]]:
    if VALUE_KEY not in payload:
        return "", JsonResponse(
            {"errorCode": "FIELD_VALUE_REQUIRED"}, status=BAD_REQUEST_STATUS
        )
    value = payload[VALUE_KEY]
    # Coercing with str() would write "None" or "{'a': 1}" into an official
    # record and mark it as the officer's own correction.
    if not isinstance(value, str):
        return "", JsonResponse(
            {"errorCode": "FIELD_VALUE_NOT_TEXT"}, status=BAD_REQUEST_STATUS
        )
    if len(value) > MAX_FIELD_VALUE_LENGTH:
        return "", JsonResponse(
            {
                "errorCode": "FIELD_VALUE_TOO_LONG",
                "maxLength": MAX_FIELD_VALUE_LENGTH,
            },
            status=BAD_REQUEST_STATUS,
        )
    return value, None


@csrf_exempt
@require_POST
@translate_domain_errors
def confirm_document_fields(
    request: HttpRequest, thread_id: str, document_id: str
) -> JsonResponse:
    change = build_confirm_document_fields_interactor().confirm_fields(
        request=ConfirmDocumentFieldsRequestDTO(
            thread_id=thread_id, document_id=document_id
        )
    )
    return JsonResponse(DocumentPresenter.get_document_change_response(change=change))


@csrf_exempt
@require_POST
@translate_domain_errors
def resolve_check(
    request: HttpRequest, thread_id: str, check_id: str
) -> JsonResponse:
    payload, error = read_json_body(request)
    if error is not None:
        return error

    change = build_resolve_check_interactor().resolve_check(
        request=ResolveCheckRequestDTO(
            thread_id=thread_id,
            check_id=check_id,
            action=str(payload.get(ACTION_KEY) or ""),
        )
    )
    return JsonResponse(DocumentPresenter.get_check_change_response(change=change))


@csrf_exempt
@require_POST
@translate_domain_errors
def retry_issuer_verification(
    request: HttpRequest, thread_id: str, document_id: str
) -> JsonResponse:
    change = build_retry_issuer_verification_interactor().retry_verification(
        request=RetryIssuerVerificationRequestDTO(
            thread_id=thread_id, document_id=document_id
        )
    )
    return JsonResponse(DocumentPresenter.get_check_change_response(change=change))


@csrf_exempt
@require_http_methods(["PUT"])
@translate_domain_errors
def update_service_overrides(request: HttpRequest, thread_id: str) -> JsonResponse:
    payload, error = read_json_body(request)
    if error is not None:
        return error
    overrides = payload.get(SERVICE_OVERRIDES_KEY, {})
    if not isinstance(overrides, dict):
        return JsonResponse(
            {"errorCode": "INVALID_SERVICE_OVERRIDES"}, status=BAD_REQUEST_STATUS
        )

    thread = build_update_service_overrides_interactor().update_overrides(
        request=UpdateServiceOverridesRequestDTO(
            thread_id=thread_id,
            service_overrides={
                str(key): str(value) for key, value in overrides.items()
            },
        )
    )
    return JsonResponse(DocumentPresenter.get_thread_response(thread=thread))


@require_GET
@translate_domain_errors
def get_scrutiny_note(request: HttpRequest, thread_id: str) -> JsonResponse:
    note = build_get_scrutiny_note_interactor().get_note(
        request=ScrutinyNoteRequestDTO(thread_id=thread_id)
    )
    return JsonResponse(DocumentPresenter.get_note_response(note=note))
