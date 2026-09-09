from document_catalog.app_interfaces.catalog_service_interface import (
    CatalogServiceInterface,
)
from document_catalog.dtos.catalog_dtos import DocumentTypeDTO, IssuerServiceDTO
from document_scrutiny.constants.upload_constants import DEFAULT_SERVICE_OVERRIDE
from document_scrutiny.domain.issuer_check import IssuerCheck
from document_scrutiny.domain.manual_verification_check import ManualVerificationCheck
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.issuer_answer_dtos import IssuerAnswerFactsDTO
from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO
from document_verification.app_interfaces.verification_service_interface import (
    VerificationServiceInterface,
)
from document_verification.dtos.verification_dtos import VerifyDocumentRequestDTO


class IssuerConsultation:
    def __init__(
        self,
        catalog_service: CatalogServiceInterface,
        verification_service: VerificationServiceInterface,
    ):
        self.catalog_service = catalog_service
        self.verification_service = verification_service

    def consult(
        self,
        thread: ScrutinyThreadDTO,
        document: DocumentStateDTO,
        document_type: DocumentTypeDTO,
    ) -> CheckDTO:
        if document_type.issuer_service_id is None:
            # Nothing to consult. Reported rather than skipped, so the officer is
            # told that no department was asked instead of having to notice that a
            # check they expect is absent.
            return ManualVerificationCheck.build(
                document_id=document.document_id,
                document_type_label=document_type.label,
            )
        issuer_service = self.catalog_service.get_issuer_service(
            issuer_service_id=document_type.issuer_service_id
        )
        answer = self.verification_service.verify_document(
            request=self._build_verify_request(
                thread=thread, document=document, issuer_service=issuer_service
            )
        )
        return IssuerCheck.build(
            document_id=document.document_id,
            issuer_service=issuer_service,
            document_type_label=document_type.label,
            facts=IssuerAnswerFactsDTO(
                outcome=answer.outcome,
                latency_ms=answer.latency_ms,
                request_payload=answer.request_payload,
                response_payload=answer.response_payload,
                disagreeing_fields=answer.disagreeing_fields,
                unreachable_reason=answer.unreachable_reason,
            ),
        )

    @staticmethod
    def _build_verify_request(
        thread: ScrutinyThreadDTO,
        document: DocumentStateDTO,
        issuer_service: IssuerServiceDTO,
    ) -> VerifyDocumentRequestDTO:
        # Everything that was read goes across, keyed by the catalog's own field
        # keys. Which of it the department actually wants is the adapter's business,
        # not this interactor's — otherwise adding an issuer means editing here too.
        return VerifyDocumentRequestDTO(
            document_id=document.document_id,
            issuer_service_id=issuer_service.issuer_service_id,
            lookup_values={value.key: value.value for value in document.field_values},
            service_override=thread.service_overrides.get(
                issuer_service.issuer_service_id, DEFAULT_SERVICE_OVERRIDE
            ),
        )
