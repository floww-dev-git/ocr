import uuid
from typing import Any, Dict, Optional

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from mock_issuer_services.constants.itd_constants import (
    REFERENCE_ID_LENGTH,
    REFERENCE_ID_PREFIX,
    SERVICE_UNAVAILABLE_STATUS,
    DemoOutcome,
    ItdFailureReason,
    ItdServerError,
    ItdVerificationStatus,
)
from mock_issuer_services.reference_data.itd_pan_records import (
    ITD_PAN_RECORDS_BY_PAN,
    ItdPanRecord,
)
from mock_issuer_services.views.issuer_demographics import dates_agree, names_agree
from mock_issuer_services.views.issuer_latency import latency_for, sleep_for
from mock_issuer_services.views.issuer_request_reader import (
    IssuerRequestRejected,
    build_rejection_response,
)
from mock_issuer_services.views.itd_request_reader import (
    ItdRequestReader,
    ItdVerifyRequestDTO,
)


@csrf_exempt
@require_POST
def verify_pan(request: HttpRequest) -> JsonResponse:
    try:
        verify_request = ItdRequestReader.read(request=request)
    except IssuerRequestRejected as rejection:
        return build_rejection_response(rejection=rejection)

    sleep_for(
        seconds=latency_for(
            demo_outcome=verify_request.demo_outcome,
            request_timeout_seconds=settings.ITD_REQUEST_TIMEOUT_SECONDS,
        )
    )
    if verify_request.demo_outcome is DemoOutcome.SERVER_ERROR:
        return JsonResponse(
            {"errorCode": ItdServerError.UPSTREAM_UNAVAILABLE.value},
            status=SERVICE_UNAVAILABLE_STATUS,
        )
    return JsonResponse(_build_answer(verify_request))


def _build_answer(verify_request: ItdVerifyRequestDTO) -> Dict[str, Any]:
    reference = {"pan": verify_request.pan, "referenceId": _build_reference_id()}
    if verify_request.demo_outcome is DemoOutcome.FAIL:
        return {**reference, **_not_matched_answer()}

    record = ITD_PAN_RECORDS_BY_PAN.get(verify_request.pan)
    if verify_request.demo_outcome is DemoOutcome.PASS:
        return {**reference, **_forced_pass_answer(record)}
    if record is None:
        return {**reference, **_not_found_answer()}
    return {**reference, **_matched_answer(verify_request=verify_request, record=record)}


def _matched_answer(
    verify_request: ItdVerifyRequestDTO, record: ItdPanRecord
) -> Dict[str, Any]:
    return _verified_answer(
        name_match=names_agree(
            submitted_name=verify_request.name, registered_name=record.registered_name
        ),
        date_of_birth_match=dates_agree(
            submitted_date=verify_request.date_of_birth,
            registered_date=record.date_of_birth,
        ),
        aadhaar_seeded=record.aadhaar_seeded,
    )


def _forced_pass_answer(record: Optional[ItdPanRecord]) -> Dict[str, Any]:
    return _verified_answer(
        name_match=True,
        date_of_birth_match=True,
        aadhaar_seeded=record.aadhaar_seeded if record is not None else True,
    )


def _verified_answer(
    name_match: bool, date_of_birth_match: Optional[bool], aadhaar_seeded: bool
) -> Dict[str, Any]:
    return {
        "status": ItdVerificationStatus.VALID.value,
        "nameMatch": name_match,
        "dobMatch": date_of_birth_match,
        "aadhaarSeeded": aadhaar_seeded,
    }


def _not_matched_answer() -> Dict[str, Any]:
    return {
        "status": ItdVerificationStatus.NOT_MATCHED.value,
        "nameMatch": None,
        "dobMatch": None,
        "reason": ItdFailureReason.DEMOGRAPHIC_MISMATCH.value,
    }


def _not_found_answer() -> Dict[str, Any]:
    return {
        "status": ItdVerificationStatus.NOT_FOUND.value,
        "nameMatch": None,
        "dobMatch": None,
        "reason": ItdFailureReason.NO_SUCH_PAN.value,
    }


def _build_reference_id() -> str:
    return f"{REFERENCE_ID_PREFIX}/{uuid.uuid4().hex[:REFERENCE_ID_LENGTH].upper()}"
