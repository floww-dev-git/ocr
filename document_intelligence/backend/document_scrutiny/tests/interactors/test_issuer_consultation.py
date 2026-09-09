from unittest.mock import create_autospec

import pytest

from document_catalog.constants.enums import DocumentTypeEnum
from document_catalog.storages.reference_data.clearance_document_specs import (
    IRRIGATION_NOC_SPEC,
)
from document_catalog.storages.reference_data.identity_document_specs import PAN_SPEC
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.issuer_check_constants import IssuerAnswerOutcome
from document_scrutiny.dtos.document_dtos import FieldValueDTO
from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO
from document_scrutiny.tests.conftest import ScrutinyStorageMock
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    DocumentStateDTOFactory,
)
from document_verification.app_interfaces.verification_service_interface import (
    VerificationServiceInterface,
)
from document_verification.dtos.verification_dtos import IssuerAnswerDTO

THREAD_ID = "thread_1"
DOCUMENT_ID = "document_1"


class TestIssuerConsultation(ScrutinyStorageMock):
    @pytest.fixture
    def verification_service(self):
        return create_autospec(VerificationServiceInterface)

    @pytest.fixture
    def consultation(self, catalog_service, verification_service):
        from document_scrutiny.interactors.issuer_consultation import (
            IssuerConsultation,
        )

        return IssuerConsultation(
            catalog_service=catalog_service,
            verification_service=verification_service,
        )

    @staticmethod
    def _thread() -> ScrutinyThreadDTO:
        return ScrutinyThreadDTO(
            thread_id=THREAD_ID,
            application_id="BN/2026/0377",
            documents=(),
            service_overrides={},
        )

    @staticmethod
    def _noc_document():
        return DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            filename="irrigation_noc.pdf",
            document_type_id=DocumentTypeEnum.IRRIGATION_NOC.value,
            document_type_label="Irrigation NOC",
            field_values=(
                FieldValueDTO(key="nocNo", value="IRR/NOC/2026/0093", confidence=0.98),
                FieldValueDTO(key="surveyNo", value="77/2", confidence=0.97),
            ),
        )

    def test_a_type_with_no_department_is_never_sent_over_the_wire(
        self, consultation, verification_service
    ):
        # Act
        consultation.consult(
            thread=self._thread(),
            document=self._noc_document(),
            document_type=IRRIGATION_NOC_SPEC,
        )

        # Assert — no call is attempted, so nothing has to be mocked out to stop one
        verification_service.verify_document.assert_not_called()

    def test_a_type_with_no_department_gets_the_manual_verification_check(
        self, consultation
    ):
        # Act
        check = consultation.consult(
            thread=self._thread(),
            document=self._noc_document(),
            document_type=IRRIGATION_NOC_SPEC,
        )

        # Assert
        assert check.check_id == f"{DOCUMENT_ID}:issuer"
        assert check.group == CheckGroup.EXTERNAL.value
        assert check.status == CheckStatus.INFO.value
        assert check.title == "No department interface for this Irrigation NOC"
        assert check.issuer_call is None

    def test_a_type_with_a_department_is_still_asked(
        self, consultation, verification_service
    ):
        # Arrange — the no-department branch must not swallow the ordinary path
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerAnswerOutcome.CONFIRMED.value,
            latency_ms=880,
            request_payload={"pan": "BNMPS7720K"},
            response_payload={"status": "VALID"},
        )
        document = DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            field_values=(
                FieldValueDTO(key="pan", value="BNMPS7720K", confidence=0.99),
            ),
        )

        # Act
        check = consultation.consult(
            thread=self._thread(), document=document, document_type=PAN_SPEC
        )

        # Assert
        verification_service.verify_document.assert_called_once()
        assert check.status == CheckStatus.PASS.value
        assert check.issuer_call is not None
        assert check.issuer_call.issuer_service_id == "itd_pan"
