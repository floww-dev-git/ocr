from document_verification.adapters.issuer_verification_interface import (
    IssuerVerificationInterface,
)
from document_verification.dtos.verification_dtos import (
    IssuerAnswerDTO,
    VerifyDocumentRequestDTO,
)


class VerifyDocumentWithIssuerInteractor:
    def __init__(self, issuer_verification: IssuerVerificationInterface):
        self.issuer_verification = issuer_verification

    def verify_document(self, request: VerifyDocumentRequestDTO) -> IssuerAnswerDTO:
        return self.issuer_verification.verify_document(request=request)
