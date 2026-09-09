import uuid
from typing import Any, Dict, List

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from mock_issuer_services.constants.issuer_http_constants import (
    SERVICE_UNAVAILABLE_STATUS,
    DemoOutcome,
)
from mock_issuer_services.constants.uidai_constants import (
    TRANSACTION_ID_LENGTH,
    TRANSACTION_ID_PREFIX,
    UidaiAuthStatus,
    UidaiDemographicField,
    UidaiFailureReason,
    UidaiServerError,
)
from mock_issuer_services.reference_data.uidai_aadhaar_records import (
    UIDAI_AADHAAR_RECORDS_BY_NUMBER,
    UidaiAadhaarRecord,
)
from mock_issuer_services.views.issuer_request_reader import (
    IssuerRequestRejected,
    build_rejection_response,
)
from mock_issuer_services.views.issuer_demographics import (
    dates_agree,
    names_agree,
    words_agree,
)
from mock_issuer_services.views.issuer_latency import latency_for, sleep_for
from mock_issuer_services.views.uidai_request_reader import (
    UidaiRequestReader,
    UidaiVerifyRequestDTO,
)


ALL_DEMOGRAPHIC_FIELDS = tuple(field.value for field in UidaiDemographicField)


@csrf_exempt
@require_POST
def verify_aadhaar(request: HttpRequest) -> JsonResponse:
    """UIDAI demographic authentication, mocked.

    Answers with which demographics agreed rather than a single yes or no, because
    that is what the real service does and it is what lets the officer see that the
    number is genuine while the name on the card is not.
    """
    try:
        verify_request = UidaiRequestReader.read(request=request)
    except IssuerRequestRejected as rejection:
        return build_rejection_response(rejection=rejection)

    sleep_for(
        seconds=latency_for(
            demo_outcome=verify_request.demo_outcome,
            request_timeout_seconds=settings.UIDAI_REQUEST_TIMEOUT_SECONDS,
        )
    )
    if verify_request.demo_outcome is DemoOutcome.SERVER_ERROR:
        return JsonResponse(
            {"errorCode": UidaiServerError.AUTH_SERVER_UNAVAILABLE.value},
            status=SERVICE_UNAVAILABLE_STATUS,
        )
    return JsonResponse(_build_answer(verify_request))


def _build_answer(verify_request: UidaiVerifyRequestDTO) -> Dict[str, Any]:
    reference = {
        "aadhaarNo": verify_request.aadhaar_number,
        "txn": _build_transaction_id(),
    }
    if verify_request.demo_outcome is DemoOutcome.FAIL:
        return {**reference, **_not_matched_answer()}

    record = UIDAI_AADHAAR_RECORDS_BY_NUMBER.get(verify_request.aadhaar_number)
    if verify_request.demo_outcome is DemoOutcome.PASS:
        return {**reference, **_matched_answer(list(ALL_DEMOGRAPHIC_FIELDS))}
    if record is None:
        return {**reference, **_not_found_answer()}
    return {
        **reference,
        **_matched_answer(
            _collect_matched_fields(verify_request=verify_request, record=record)
        ),
    }


def _collect_matched_fields(
    verify_request: UidaiVerifyRequestDTO, record: UidaiAadhaarRecord
) -> List[str]:
    matched: List[str] = []
    if names_agree(verify_request.name, record.registered_name):
        matched.append(UidaiDemographicField.NAME.value)
    # A demographic that was not submitted is not reported as disagreeing: UIDAI
    # only answers on what it was asked about.
    if verify_request.date_of_birth is None or dates_agree(
        verify_request.date_of_birth, record.date_of_birth
    ):
        matched.append(UidaiDemographicField.DATE_OF_BIRTH.value)
    if verify_request.gender is None or words_agree(
        verify_request.gender, record.gender
    ):
        matched.append(UidaiDemographicField.GENDER.value)
    return matched


def _matched_answer(matched: List[str]) -> Dict[str, Any]:
    return {"status": UidaiAuthStatus.MATCHED.value, "matched": matched}


def _not_matched_answer() -> Dict[str, Any]:
    return {
        "status": UidaiAuthStatus.NOT_MATCHED.value,
        "matched": [],
        "reason": UidaiFailureReason.DEMOGRAPHIC_MISMATCH.value,
    }


def _not_found_answer() -> Dict[str, Any]:
    return {
        "status": UidaiAuthStatus.NOT_FOUND.value,
        "matched": [],
        "reason": UidaiFailureReason.NO_SUCH_AADHAAR.value,
    }


def _build_transaction_id() -> str:
    return (
        f"{TRANSACTION_ID_PREFIX}-"
        f"{uuid.uuid4().hex[:TRANSACTION_ID_LENGTH].upper()}"
    )
