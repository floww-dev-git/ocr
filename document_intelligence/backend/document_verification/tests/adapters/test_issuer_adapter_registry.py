import pytest

from document_catalog.constants.enums import IssuerServiceEnum
from document_verification.adapters.issuer_adapter_registry import get_issuer_adapter
from document_verification.adapters.issuer_verification_interface import (
    IssuerVerificationInterface,
)
from document_verification.exceptions.verification_exceptions import (
    IssuerAdapterNotRegistered,
)


class TestGetIssuerAdapter:
    @pytest.mark.parametrize(
        "issuer_service_id",
        [
            IssuerServiceEnum.ITD_PAN.value,
            IssuerServiceEnum.UIDAI.value,
            IssuerServiceEnum.SARATHI.value,
            IssuerServiceEnum.IGRS.value,
        ],
    )
    def test_a_wired_department_resolves_to_an_adapter_honouring_the_port(
        self, issuer_service_id
    ):
        # Act
        adapter = get_issuer_adapter(issuer_service_id=issuer_service_id)

        # Assert
        assert isinstance(adapter, IssuerVerificationInterface)

    @pytest.mark.parametrize(
        "issuer_service_id",
        [
            IssuerServiceEnum.FIRE_REGISTRY.value,
            IssuerServiceEnum.AAI_NOCAS.value,
            IssuerServiceEnum.ULB_REGISTRY.value,
            "",
        ],
    )
    def test_a_department_this_build_cannot_call_is_refused_not_reported_unreachable(
        self, issuer_service_id
    ):
        # Arrange — an `unreachable` outcome offers the officer a retry. Retrying a
        # call that was never wired would spin forever, so this is not that.
        # Act & Assert
        with pytest.raises(IssuerAdapterNotRegistered) as exception_info:
            get_issuer_adapter(issuer_service_id=issuer_service_id)
        assert exception_info.value.issuer_service_id == issuer_service_id

    def test_each_call_builds_its_own_adapter_rather_than_sharing_one(self):
        # Arrange — adapters carry a transport, so sharing one across threads would
        # share a connection pool the callers never agreed to share.
        # Act
        first = get_issuer_adapter(issuer_service_id=IssuerServiceEnum.ITD_PAN.value)
        second = get_issuer_adapter(issuer_service_id=IssuerServiceEnum.ITD_PAN.value)

        # Assert
        assert first is not second
