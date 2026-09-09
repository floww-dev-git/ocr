import functools
import json
from typing import Any, Dict, Optional, Tuple

from django.http import HttpRequest, JsonResponse

from api.error_responses import BAD_REQUEST_STATUS, build_error_response


def translate_domain_errors(view):
    """Turns the domain's refusals into HTTP answers, and lets anything
    unrecognised keep travelling so it is never silently swallowed."""

    @functools.wraps(view)
    def _wrapped(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except Exception as error_raised:
            mapped = build_error_response(error_raised)
            if mapped is None:
                raise
            return mapped

    return _wrapped


def read_json_body(request: HttpRequest) -> Tuple[Dict[str, Any], Optional[JsonResponse]]:
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}, _invalid_body()
    if not isinstance(payload, dict):
        return {}, _invalid_body()
    return payload, None


def _invalid_body() -> JsonResponse:
    return JsonResponse(
        {"errorCode": "INVALID_REQUEST_BODY"}, status=BAD_REQUEST_STATUS
    )
