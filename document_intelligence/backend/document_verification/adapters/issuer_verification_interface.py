import abc

from document_verification.dtos.verification_dtos import (
    IssuerAnswerDTO,
    VerifyDocumentRequestDTO,
)


class IssuerVerificationInterface(abc.ABC):
    @abc.abstractmethod
    def verify_document(self, request: VerifyDocumentRequestDTO) -> IssuerAnswerDTO:
        pass
