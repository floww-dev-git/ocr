from typing import Any, Dict, Optional

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET

from mock_issuer_services.constants.igrs_constants import (
    IgrsDeedStatus,
    IgrsFailureReason,
    IgrsServerError,
)
from mock_issuer_services.constants.issuer_http_constants import (
    SERVICE_UNAVAILABLE_STATUS,
    DemoOutcome,
)
from mock_issuer_services.reference_data.igrs_deed_records import (
    IGRS_DEED_RECORDS_BY_DOCUMENT_NUMBER,
    IgrsDeedRecord,
)
from mock_issuer_services.views.igrs_request_reader import (
    IgrsLookupRequestDTO,
    IgrsRequestReader,
)
from mock_issuer_services.views.issuer_demographics import names_agree
from mock_issuer_services.views.issuer_latency import latency_for, sleep_for
from mock_issuer_services.views.issuer_request_reader import (
    IssuerRequestRejected,
    build_rejection_response,
)


@require_GET
def look_up_deed(request: HttpRequest, doc_no: str) -> JsonResponse:
    """IGRS's registered-deed lookup, mocked.

    Answers with the parties and extent the register holds, so the officer can see
    that a deed is genuinely registered and whether it was registered between the
    people the paper in front of them names.
    """
    try:
        lookup_request = IgrsRequestReader.read(request=request, doc_no=doc_no)
    except IssuerRequestRejected as rejection:
        return build_rejection_response(rejection=rejection)

    sleep_for(
        seconds=latency_for(
            demo_outcome=lookup_request.demo_outcome,
            request_timeout_seconds=settings.IGRS_REQUEST_TIMEOUT_SECONDS,
        )
    )
    if lookup_request.demo_outcome is DemoOutcome.SERVER_ERROR:
        return JsonResponse(
            {"errorCode": IgrsServerError.IGRS_UNAVAILABLE.value},
            status=SERVICE_UNAVAILABLE_STATUS,
        )
    return JsonResponse(_build_answer(lookup_request))


def _build_answer(lookup_request: IgrsLookupRequestDTO) -> Dict[str, Any]:
    reference = {"docNo": lookup_request.doc_no}
    if lookup_request.demo_outcome is DemoOutcome.FAIL:
        return {**reference, **_not_matched_answer()}

    record = IGRS_DEED_RECORDS_BY_DOCUMENT_NUMBER.get(lookup_request.doc_no)
    if lookup_request.demo_outcome is DemoOutcome.PASS:
        return {**reference, **_forced_pass_answer(record)}
    if record is None:
        return {**reference, **_not_found_answer()}
    return {
        **reference,
        **_registered_answer(
            record=record,
            # The claimant is the person the deed conveyed the property TO, which is
            # who the application should be in the name of.
            name_match=names_agree(lookup_request.name, record.claimant),
        ),
    }


def _forced_pass_answer(record: Optional[IgrsDeedRecord]) -> Dict[str, Any]:
    if record is None:
        return {
            "status": IgrsDeedStatus.REGISTERED.value,
            "sro": None,
            "executant": None,
            "claimant": None,
            "extent": None,
            "registrationDate": None,
            "nameMatch": True,
        }
    return _registered_answer(record=record, name_match=True)


def _registered_answer(record: IgrsDeedRecord, name_match: bool) -> Dict[str, Any]:
    return {
        "status": IgrsDeedStatus.REGISTERED.value,
        "sro": record.sro,
        "executant": record.executant,
        "claimant": record.claimant,
        "extent": record.extent,
        "registrationDate": record.registration_date,
        "nameMatch": name_match,
    }


def _not_matched_answer() -> Dict[str, Any]:
    return {
        "status": IgrsDeedStatus.NOT_MATCHED.value,
        "nameMatch": None,
        "reason": IgrsFailureReason.PARTY_MISMATCH.value,
    }


def _not_found_answer() -> Dict[str, Any]:
    return {
        "status": IgrsDeedStatus.NOT_FOUND.value,
        "nameMatch": None,
        "reason": IgrsFailureReason.NO_SUCH_DEED.value,
    }
