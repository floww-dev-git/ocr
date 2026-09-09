import time

from django.conf import settings

from mock_issuer_services.constants.issuer_http_constants import DemoOutcome


def sleep_for(seconds: float) -> None:
    if seconds > 0:
        time.sleep(seconds)


def latency_for(demo_outcome: DemoOutcome, request_timeout_seconds: float) -> float:
    """How long this department takes to answer.

    A forced timeout waits past the caller's own budget plus a margin, so the
    officer sees a genuine wait rather than an instant failure dressed up as one —
    the wait is part of what they are being shown.
    """
    if demo_outcome is DemoOutcome.TIMEOUT:
        return float(request_timeout_seconds) + float(
            settings.MOCK_ISSUER_TIMEOUT_MARGIN_SECONDS
        )
    return float(settings.MOCK_ISSUER_LATENCY_SECONDS)
