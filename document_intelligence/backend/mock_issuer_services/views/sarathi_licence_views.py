from typing import Any, Dict, Optional

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from mock_issuer_services.constants.issuer_http_constants import (
    SERVICE_UNAVAILABLE_STATUS,
    DemoOutcome,
)
from mock_issuer_services.constants.sarathi_constants import (
    SarathiFailureReason,
    SarathiLicenceStatus,
    SarathiServerError,
)
from mock_issuer_services.reference_data.sarathi_licence_records import (
    SARATHI_LICENCE_RECORDS_BY_NUMBER,
    SarathiLicenceRecord,
)
from mock_issuer_services.views.issuer_demographics import dates_agree, names_agree
from mock_issuer_services.views.issuer_latency import latency_for, sleep_for
from mock_issuer_services.views.issuer_request_reader import (
    IssuerRequestRejected,
    build_rejection_response,
)
from mock_issuer_services.views.sarathi_request_reader import (
    SarathiLookupRequestDTO,
    SarathiRequestReader,
)


@require_GET
def look_up_licence(request: HttpRequest, licence_number: str) -> JsonResponse:
    """Sarathi's driving licence lookup, mocked.

    A lookup rather than a post, matching the real service, and it answers with the
    record it holds so the officer can see what the department has on file.
    """
    try:
        lookup_request = SarathiRequestReader.read(
            request=request, licence_number=licence_number
        )
    except IssuerRequestRejected as rejection:
        return build_rejection_response(rejection=rejection)

    sleep_for(
        seconds=latency_for(
            demo_outcome=lookup_request.demo_outcome,
            request_timeout_seconds=settings.SARATHI_REQUEST_TIMEOUT_SECONDS,
        )
    )
    if lookup_request.demo_outcome is DemoOutcome.SERVER_ERROR:
        return JsonResponse(
            {"errorCode": SarathiServerError.SARATHI_UNAVAILABLE.value},
            status=SERVICE_UNAVAILABLE_STATUS,
        )
    return JsonResponse(_build_answer(lookup_request))


def _build_answer(lookup_request: SarathiLookupRequestDTO) -> Dict[str, Any]:
    reference = {"dlNo": lookup_request.licence_number}
    if lookup_request.demo_outcome is DemoOutcome.FAIL:
        return {**reference, **_not_matched_answer()}

    record = SARATHI_LICENCE_RECORDS_BY_NUMBER.get(lookup_request.licence_number)
    if lookup_request.demo_outcome is DemoOutcome.PASS:
        return {**reference, **_forced_pass_answer(record)}
    if record is None:
        return {**reference, **_not_found_answer()}
    return {
        **reference,
        **_held_answer(lookup_request=lookup_request, record=record),
    }


def _held_answer(
    lookup_request: SarathiLookupRequestDTO, record: SarathiLicenceRecord
) -> Dict[str, Any]:
    return _active_answer(
        record=record,
        name_match=names_agree(lookup_request.name, record.holder_name),
        date_of_birth_match=dates_agree(
            lookup_request.date_of_birth, record.date_of_birth
        ),
    )


def _forced_pass_answer(record: Optional[SarathiLicenceRecord]) -> Dict[str, Any]:
    if record is None:
        return {
            "status": SarathiLicenceStatus.ACTIVE.value,
            "holder": None,
            "dob": None,
            "validUpto": None,
            "cov": [],
            "nameMatch": True,
            "dobMatch": True,
        }
    return _active_answer(record=record, name_match=True, date_of_birth_match=True)


def _active_answer(
    record: SarathiLicenceRecord,
    name_match: bool,
    date_of_birth_match: Optional[bool],
) -> Dict[str, Any]:
    return {
        "status": SarathiLicenceStatus.ACTIVE.value,
        "holder": record.holder_name,
        "dob": record.date_of_birth,
        "validUpto": record.valid_until,
        "cov": list(record.vehicle_classes),
        "nameMatch": name_match,
        "dobMatch": date_of_birth_match,
    }


def _not_matched_answer() -> Dict[str, Any]:
    return {
        "status": SarathiLicenceStatus.NOT_MATCHED.value,
        "nameMatch": None,
        "dobMatch": None,
        "reason": SarathiFailureReason.HOLDER_MISMATCH.value,
    }


def _not_found_answer() -> Dict[str, Any]:
    return {
        "status": SarathiLicenceStatus.NOT_FOUND.value,
        "nameMatch": None,
        "dobMatch": None,
        "reason": SarathiFailureReason.NO_SUCH_LICENCE.value,
    }
