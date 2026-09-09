from unittest.mock import create_autospec

import pytest

from document_scrutiny.constants.enums import CheckGroup, CheckStatus, ThreadStatus
from document_scrutiny.constants.issuer_check_constants import IssuerAnswerOutcome
from document_scrutiny.dtos.officer_action_dtos import (
    RetryIssuerVerificationRequestDTO,
)
from document_scrutiny.exceptions.scrutiny_exceptions import (
    CheckNotRetryable,
    IssuerCheckMissing,
    NoIssuerToRetry,
)
from document_scrutiny.tests.conftest import (
    ScrutinyStorageMock,
    build_pan_field_values,
    wire_document_memory,
)
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    CheckDTOFactory,
    DocumentStateDTOFactory,
)
from document_verification.app_interfaces.verification_service_interface import (
    VerificationServiceInterface,
)
from document_verification.constants.verification_constants import (
    ServiceOverride,
    UnreachableReason,
)
from document_verification.dtos.verification_dtos import IssuerAnswerDTO

THREAD_ID = "thread_1"
DOCUMENT_ID = "document_1"
ISSUER_CHECK_ID = f"{DOCUMENT_ID}:issuer"


class TestRetryIssuerVerificationInteractor(ScrutinyStorageMock):
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

    @pytest.fixture
    def interactor(self, thread_storage, catalog_service, consultation):
        from document_scrutiny.interactors.retry_issuer_verification_interactor import (
            RetryIssuerVerificationInteractor,
        )

        return RetryIssuerVerificationInteractor(
            thread_storage=thread_storage,
            catalog_service=catalog_service,
            consultation=consultation,
        )

    def _document_with(self, issuer_check=None, checks=None):
        if checks is None:
            checks = () if issuer_check is None else (issuer_check,)
        return DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            document_type_id="pan",
            field_values=build_pan_field_values(
                name="MOHAMMED IRFAN SIDDIQUI",
                parent_name="MOHAMMED YOUSUF SIDDIQUI",
                date_of_birth="1982-11-27",
                pan="BNMPS7720K",
            ),
            checks=checks,
        )

    @staticmethod
    def _issuer_check(status: str, acknowledged: bool = False):
        return CheckDTOFactory(
            check_id=ISSUER_CHECK_ID,
            document_id=DOCUMENT_ID,
            group=CheckGroup.EXTERNAL.value,
            status=status,
            title="Income Tax PAN verification did not respond",
            acknowledged=acknowledged,
        )

    def _retry(self, interactor):
        return interactor.retry_verification(
            request=RetryIssuerVerificationRequestDTO(
                thread_id=THREAD_ID, document_id=DOCUMENT_ID
            )
        )

    def test_a_retry_that_succeeds_replaces_the_earlier_answer(
        self, interactor, thread_storage, verification_service
    ):
        # Arrange
        wire_document_memory(
            thread_storage=thread_storage,
            documents=(
                self._document_with(
                    self._issuer_check(CheckStatus.UNAVAILABLE.value)
                ),
            ),
        )
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerAnswerOutcome.CONFIRMED.value,
            latency_ms=812,
            request_payload={"pan": "BNMPS7720K"},
            response_payload={"status": "VALID"},
        )

        # Act
        change = self._retry(interactor)

        # Assert
        assert change.check.status == CheckStatus.PASS.value
        assert change.summary.thread_status == ThreadStatus.CLEAR.value

    def test_the_replacement_keeps_the_place_of_the_answer_it_supersedes(
        self, interactor, thread_storage, verification_service
    ):
        # Arrange
        rule_check = CheckDTOFactory(
            check_id=f"{DOCUMENT_ID}:name", document_id=DOCUMENT_ID
        )
        wire_document_memory(
            thread_storage=thread_storage,
            documents=(
                self._document_with(
                    checks=(
                        rule_check,
                        self._issuer_check(CheckStatus.UNAVAILABLE.value),
                    )
                ),
            ),
        )
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerAnswerOutcome.CONFIRMED.value, latency_ms=700
        )

        # Act
        change = self._retry(interactor)

        # Assert
        assert [check.check_id for check in change.document.checks] == [
            rule_check.check_id,
            ISSUER_CHECK_ID,
        ]

    def test_a_fresh_answer_arrives_unresolved(
        self, interactor, thread_storage, verification_service
    ):
        # Arrange
        wire_document_memory(
            thread_storage=thread_storage,
            documents=(
                self._document_with(
                    self._issuer_check(
                        CheckStatus.UNAVAILABLE.value, acknowledged=True
                    )
                ),
            ),
        )
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerAnswerOutcome.NOT_MATCHED.value, latency_ms=640
        )

        # Act
        change = self._retry(interactor)

        # Assert
        assert change.check.acknowledged is False
        assert change.summary.thread_status == ThreadStatus.ATTENTION.value

    def test_a_retry_that_fails_again_says_so(
        self, interactor, thread_storage, verification_service
    ):
        # Arrange
        wire_document_memory(
            thread_storage=thread_storage,
            documents=(
                self._document_with(
                    self._issuer_check(CheckStatus.UNAVAILABLE.value)
                ),
            ),
        )
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerAnswerOutcome.UNREACHABLE.value,
            latency_ms=3000,
            unreachable_reason=UnreachableReason.CONNECTION_FAILED.value,
        )

        # Act
        change = self._retry(interactor)

        # Assert
        assert change.check.status == CheckStatus.UNAVAILABLE.value

    def test_a_department_that_already_agreed_is_not_asked_again(
        self, interactor, thread_storage, verification_service
    ):
        # Arrange
        wire_document_memory(
            thread_storage=thread_storage,
            documents=(self._document_with(self._issuer_check(CheckStatus.PASS.value)),),
        )

        # Act & Assert
        with pytest.raises(CheckNotRetryable) as raised:
            self._retry(interactor)

        assert raised.value.check_id == ISSUER_CHECK_ID
        verification_service.verify_document.assert_not_called()
        thread_storage.update_document.assert_not_called()

    def test_a_type_whose_department_has_no_interface_cannot_be_retried(
        self, interactor, thread_storage, verification_service
    ):
        # Arrange — an Irrigation NOC was never asked, so there is nothing to re-ask
        noc = DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            filename="irrigation_noc.pdf",
            document_type_id="irrigation_noc",
            document_type_label="Irrigation NOC",
            checks=(
                CheckDTOFactory(
                    check_id=ISSUER_CHECK_ID,
                    document_id=DOCUMENT_ID,
                    group=CheckGroup.EXTERNAL.value,
                    status=CheckStatus.INFO.value,
                    title="No department interface for this Irrigation NOC",
                ),
            ),
        )
        wire_document_memory(thread_storage=thread_storage, documents=(noc,))

        # Act & Assert
        with pytest.raises(NoIssuerToRetry) as raised:
            self._retry(interactor)

        assert raised.value.document_id == DOCUMENT_ID
        verification_service.verify_document.assert_not_called()
        thread_storage.update_document.assert_not_called()

    def test_a_document_never_sent_for_verification_cannot_be_retried(
        self, interactor, thread_storage, verification_service
    ):
        # Arrange
        wire_document_memory(
            thread_storage=thread_storage, documents=(self._document_with(),)
        )

        # Act & Assert
        with pytest.raises(IssuerCheckMissing) as raised:
            self._retry(interactor)

        assert raised.value.document_id == DOCUMENT_ID
        verification_service.verify_document.assert_not_called()

    def test_the_retry_carries_the_values_now_on_the_document(
        self, interactor, thread_storage, verification_service
    ):
        # Arrange
        wire_document_memory(
            thread_storage=thread_storage,
            documents=(
                self._document_with(
                    self._issuer_check(CheckStatus.UNAVAILABLE.value)
                ),
            ),
        )
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerAnswerOutcome.CONFIRMED.value, latency_ms=500
        )

        # Act
        self._retry(interactor)

        # Assert
        sent = verification_service.verify_document.call_args.kwargs["request"]
        assert sent.lookup_values["pan"] == "BNMPS7720K"
        assert sent.lookup_values["name"] == "MOHAMMED IRFAN SIDDIQUI"
        assert sent.lookup_values["dob"] == "1982-11-27"

    def test_the_threads_forced_answer_is_honoured_on_retry(
        self, interactor, thread_storage, verification_service
    ):
        # Arrange
        wire_document_memory(
            thread_storage=thread_storage,
            documents=(
                self._document_with(
                    self._issuer_check(CheckStatus.UNAVAILABLE.value)
                ),
            ),
            service_overrides={"itd_pan": ServiceOverride.TIMEOUT.value},
        )
        verification_service.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerAnswerOutcome.UNREACHABLE.value, latency_ms=3000
        )

        # Act
        self._retry(interactor)

        # Assert
        sent = verification_service.verify_document.call_args.kwargs["request"]
        assert sent.service_override == ServiceOverride.TIMEOUT.value
