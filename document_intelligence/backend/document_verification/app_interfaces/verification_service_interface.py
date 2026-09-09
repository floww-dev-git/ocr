from document_verification.adapters.issuer_adapter_registry import get_issuer_adapter
from document_verification.dtos.verification_dtos import (
    IssuerAnswerDTO,
    VerifyDocumentRequestDTO,
)
from document_verification.interactors.verify_document_with_issuer_interactor import (
    VerifyDocumentWithIssuerInteractor,
)


class VerificationServiceInterface:
    def verify_document(self, request: VerifyDocumentRequestDTO) -> IssuerAnswerDTO:
        interactor = VerifyDocumentWithIssuerInteractor(
            issuer_verification=get_issuer_adapter(
                issuer_service_id=request.issuer_service_id
            )
        )
        return interactor.verify_document(request=request)
