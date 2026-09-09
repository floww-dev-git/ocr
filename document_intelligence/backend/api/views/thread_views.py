from typing import List

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from api.error_responses import BAD_REQUEST_STATUS
from api.interactor_factory import (
    build_add_documents_to_thread_interactor,
    build_create_scrutiny_thread_interactor,
    build_get_scrutiny_thread_interactor,
)
from api.request_handling import read_json_body, translate_domain_errors
from document_scrutiny.dtos.thread_dtos import (
    AddDocumentsRequestDTO,
    CreateScrutinyThreadDTO,
    IncomingFileDTO,
)
from document_scrutiny.presenters.document_presenter import DocumentPresenter

CREATED_STATUS = 201
UPLOAD_FIELD_NAME = "files"


@csrf_exempt
@require_POST
@translate_domain_errors
def create_scrutiny_thread(request: HttpRequest) -> JsonResponse:
    payload, error = read_json_body(request)
    if error is not None:
        return error
    application_id = str(payload.get("applicationId") or "").strip()
    if not application_id:
        return JsonResponse(
            {"errorCode": "APPLICATION_ID_REQUIRED"}, status=BAD_REQUEST_STATUS
        )

    thread = build_create_scrutiny_thread_interactor().create_scrutiny_thread(
        create_thread=CreateScrutinyThreadDTO(application_id=application_id)
    )
    return JsonResponse(
        DocumentPresenter.get_thread_response(thread=thread), status=CREATED_STATUS
    )


@require_GET
@translate_domain_errors
def get_scrutiny_thread(request: HttpRequest, thread_id: str) -> JsonResponse:
    thread = build_get_scrutiny_thread_interactor().get_thread(thread_id=thread_id)
    return JsonResponse(DocumentPresenter.get_thread_response(thread=thread))


@csrf_exempt
@require_POST
@translate_domain_errors
def add_documents(request: HttpRequest, thread_id: str) -> JsonResponse:
    incoming_files = _read_incoming_files(request)
    if not incoming_files:
        return JsonResponse(
            {"errorCode": "NO_FILES_ATTACHED"}, status=BAD_REQUEST_STATUS
        )

    documents = build_add_documents_to_thread_interactor().add_documents(
        request=AddDocumentsRequestDTO(
            thread_id=thread_id, incoming_files=tuple(incoming_files)
        )
    )
    return JsonResponse(
        DocumentPresenter.get_documents_response(documents=documents),
        status=CREATED_STATUS,
    )


def _read_incoming_files(request: HttpRequest) -> List[IncomingFileDTO]:
    return [
        IncomingFileDTO(filename=uploaded.name, content=uploaded.read())
        for uploaded in request.FILES.getlist(UPLOAD_FIELD_NAME)
    ]
