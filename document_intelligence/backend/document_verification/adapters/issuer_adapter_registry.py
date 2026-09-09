from typing import Callable, Dict

from document_catalog.constants.enums import IssuerServiceEnum
from document_verification.adapters.issuer_verification_interface import (
    IssuerVerificationInterface,
)
from document_verification.exceptions.verification_exceptions import (
    IssuerAdapterNotRegistered,
)


def _build_itd_pan_adapter() -> IssuerVerificationInterface:
    from document_verification.adapters.itd_pan_service_adapter import (
        ItdPanServiceAdapter,
    )

    return ItdPanServiceAdapter()


def _build_uidai_adapter() -> IssuerVerificationInterface:
    from document_verification.adapters.uidai_service_adapter import (
        UidaiServiceAdapter,
    )

    return UidaiServiceAdapter()


def _build_sarathi_adapter() -> IssuerVerificationInterface:
    from document_verification.adapters.sarathi_service_adapter import (
        SarathiServiceAdapter,
    )

    return SarathiServiceAdapter()


def _build_igrs_adapter() -> IssuerVerificationInterface:
    from document_verification.adapters.igrs_deed_service_adapter import (
        IgrsDeedServiceAdapter,
    )

    return IgrsDeedServiceAdapter()


# One entry per department this build can actually call. A catalog document type
# pointing at an issuer with no entry here is a wiring mistake, and is reported as
# one rather than as a department that failed to answer.
_ADAPTER_BUILDERS_BY_ISSUER_SERVICE: Dict[
    str, Callable[[], IssuerVerificationInterface]
] = {
    IssuerServiceEnum.ITD_PAN.value: _build_itd_pan_adapter,
    IssuerServiceEnum.UIDAI.value: _build_uidai_adapter,
    IssuerServiceEnum.SARATHI.value: _build_sarathi_adapter,
    IssuerServiceEnum.IGRS.value: _build_igrs_adapter,
}


def get_issuer_adapter(issuer_service_id: str) -> IssuerVerificationInterface:
    builder = _ADAPTER_BUILDERS_BY_ISSUER_SERVICE.get(str(issuer_service_id or ""))
    if builder is None:
        raise IssuerAdapterNotRegistered(
            issuer_service_id=str(issuer_service_id or "")
        )
    return builder()
