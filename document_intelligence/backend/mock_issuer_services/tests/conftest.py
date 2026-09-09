import json
from typing import Any, Dict, Optional

import pytest
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse

from mock_issuer_services.constants.itd_constants import (
    API_KEY_HEADER,
    DEMO_OUTCOME_HEADER,
)

VERIFY_URL_NAME = "mock_itd_verify_pan"
DEMO_API_KEY = "poc-itd-demo-key"

CLEAN_PAN = "DQRPK4831L"
CLEAN_NAME = "SRINIVAS RAO KANDULA"
CLEAN_DATE_OF_BIRTH = "1979-08-14"
MISMATCH_PAN = "BNMPS7720K"
MISMATCH_READ_NAME = "MOHAMMED IRFAN SIDDIQI"
MISMATCH_DATE_OF_BIRTH = "1982-11-27"
UNHELD_PAN = "ZZZPZ9999Z"


def build_payload(
    pan: str = CLEAN_PAN,
    name: Optional[str] = CLEAN_NAME,
    date_of_birth: Optional[str] = CLEAN_DATE_OF_BIRTH,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"pan": pan}
    if name is not None:
        payload["name"] = name
    if date_of_birth is not None:
        payload["dob"] = date_of_birth
    return payload


def post_verify(
    client: Client,
    payload: Optional[Dict[str, Any]] = None,
    demo_outcome: Optional[str] = None,
    raw_body: Optional[str] = None,
    api_key: Optional[str] = DEMO_API_KEY,
) -> HttpResponse:
    headers: Dict[str, str] = {}
    if api_key is not None:
        headers[API_KEY_HEADER] = api_key
    if demo_outcome is not None:
        headers[DEMO_OUTCOME_HEADER] = demo_outcome
    body = raw_body if raw_body is not None else json.dumps(
        payload if payload is not None else build_payload()
    )
    return client.post(
        reverse(VERIFY_URL_NAME),
        data=body,
        content_type="application/json",
        headers=headers,
    )


class IssuerClientMock:
    @pytest.fixture
    def client(self) -> Client:
        return Client()

    @pytest.fixture(autouse=True)
    def instant_issuer(self, settings):
        settings.MOCK_ISSUER_LATENCY_SECONDS = 0
        settings.MOCK_ISSUER_TIMEOUT_MARGIN_SECONDS = 0
        settings.MOCK_ISSUER_API_KEY = DEMO_API_KEY
        settings.DEBUG = True
