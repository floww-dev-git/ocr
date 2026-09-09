import pytest

from document_verification.constants.verification_constants import (
    IssuerOutcome,
    ServiceOverride,
)
from document_verification.dtos.verification_dtos import (
    IssuerAnswerDTO,
    VerifyDocumentRequestDTO,
)


class IssuerVerificationMock:
    @pytest.fixture
    def issuer_verification(self):
        from unittest.mock import create_autospec

        from document_verification.adapters.issuer_verification_interface import (
            IssuerVerificationInterface,
        )

        return create_autospec(IssuerVerificationInterface)


class TestVerifyDocumentWithIssuerInteractor(IssuerVerificationMock):
    @pytest.fixture
    def interactor(self, issuer_verification):
        from document_verification.interactors.verify_document_with_issuer_interactor import (
            VerifyDocumentWithIssuerInteractor,
        )

        return VerifyDocumentWithIssuerInteractor(issuer_verification=issuer_verification)

    @pytest.fixture
    def request_dto(self):
        return VerifyDocumentRequestDTO(
            document_id="document_1",
            issuer_service_id="itd_pan",
            lookup_values={
                "pan": "DQRPK4831L",
                "name": "SRINIVAS RAO KANDULA",
                "dob": "1979-08-14",
            },
        )

    def test_an_unreachable_issuer_is_returned_rather_than_raised(
        self, interactor, issuer_verification, request_dto
    ):
        # Arrange — AC7
        issuer_verification.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.UNREACHABLE.value, latency_ms=3000
        )

        # Act
        answer = interactor.verify_document(request=request_dto)

        # Assert
        assert answer.outcome == IssuerOutcome.UNREACHABLE.value

    def test_the_issuer_is_asked_exactly_once_with_the_request_it_was_given(
        self, interactor, issuer_verification, request_dto
    ):
        # Arrange
        issuer_verification.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.CONFIRMED.value, latency_ms=912
        )

        # Act
        interactor.verify_document(request=request_dto)

        # Assert
        issuer_verification.verify_document.assert_called_once_with(request=request_dto)

    def test_a_forced_outcome_is_carried_through_to_the_issuer(
        self, interactor, issuer_verification
    ):
        # Arrange
        forced_request = VerifyDocumentRequestDTO(
            document_id="document_1",
            issuer_service_id="itd_pan",
            lookup_values={"pan": "DQRPK4831L", "name": "SRINIVAS RAO KANDULA"},
            service_override=ServiceOverride.FAIL.value,
        )
        issuer_verification.verify_document.return_value = IssuerAnswerDTO(
            outcome=IssuerOutcome.NOT_MATCHED.value, latency_ms=900
        )

        # Act
        answer = interactor.verify_document(request=forced_request)

        # Assert
        issuer_verification.verify_document.assert_called_once_with(request=forced_request)
        assert answer.outcome == IssuerOutcome.NOT_MATCHED.value

    def test_the_answer_is_returned_untouched(
        self, interactor, issuer_verification, request_dto
    ):
        # Arrange
        issuer_answer = IssuerAnswerDTO(
            outcome=IssuerOutcome.PARTIAL_MATCH.value,
            latency_ms=912,
            request_payload={"pan": "DQRPK4831L"},
            response_payload={"status": "VALID", "nameMatch": False},
            disagreeing_fields=("name",),
        )
        issuer_verification.verify_document.return_value = issuer_answer

        # Act
        answer = interactor.verify_document(request=request_dto)

        # Assert
        assert answer is issuer_answer
