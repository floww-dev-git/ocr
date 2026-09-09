from django.conf import settings

from document_scrutiny.adapters.local_document_file_store import LocalDocumentFileStore
from document_scrutiny.adapters.logging_failure_reporter import LoggingFailureReporter
from document_scrutiny.adapters.service_adapter import get_service_adapter
from document_scrutiny.dtos.thread_dtos import UploadLimitsDTO
from document_scrutiny.interactors.add_documents_to_thread_interactor import (
    AddDocumentsToThreadInteractor,
)
from document_scrutiny.interactors.analyze_document_interactor import (
    AnalyzeDocumentInteractor,
)
from document_scrutiny.interactors.analyze_thread_interactor import (
    AnalyzeThreadInteractor,
)
from document_scrutiny.interactors.confirm_document_fields_interactor import (
    ConfirmDocumentFieldsInteractor,
)
from document_scrutiny.interactors.create_scrutiny_thread_interactor import (
    CreateScrutinyThreadInteractor,
)
from document_scrutiny.interactors.get_chain_of_title_interactor import (
    GetChainOfTitleInteractor,
)
from document_scrutiny.interactors.get_ownership_report_interactor import (
    GetOwnershipReportInteractor,
)
from document_scrutiny.interactors.get_scrutiny_note_interactor import (
    GetScrutinyNoteInteractor,
)
from document_scrutiny.interactors.get_scrutiny_thread_interactor import (
    GetScrutinyThreadInteractor,
)
from document_scrutiny.interactors.issuer_consultation import IssuerConsultation
from document_scrutiny.interactors.resolve_check_interactor import (
    ResolveCheckInteractor,
)
from document_scrutiny.interactors.retry_issuer_verification_interactor import (
    RetryIssuerVerificationInteractor,
)
from document_scrutiny.interactors.segment_bundle_interactor import (
    SegmentBundleInteractor,
)
from document_scrutiny.interactors.update_document_field_interactor import (
    UpdateDocumentFieldInteractor,
)
from document_scrutiny.interactors.update_service_overrides_interactor import (
    UpdateServiceOverridesInteractor,
)
from document_scrutiny.storages.in_memory_scrutiny_thread_storage import (
    InMemoryScrutinyThreadStorage,
)


def build_create_scrutiny_thread_interactor() -> CreateScrutinyThreadInteractor:
    return CreateScrutinyThreadInteractor(
        thread_storage=InMemoryScrutinyThreadStorage(),
        catalog_service=get_service_adapter().catalog_service,
    )


def build_get_scrutiny_thread_interactor() -> GetScrutinyThreadInteractor:
    return GetScrutinyThreadInteractor(thread_storage=InMemoryScrutinyThreadStorage())


def build_add_documents_to_thread_interactor() -> AddDocumentsToThreadInteractor:
    return AddDocumentsToThreadInteractor(
        thread_storage=InMemoryScrutinyThreadStorage(),
        document_file_store=LocalDocumentFileStore(),
        upload_limits=build_upload_limits(),
    )


def build_upload_limits() -> UploadLimitsDTO:
    return UploadLimitsDTO(
        allowed_extensions=tuple(settings.ALLOWED_UPLOAD_EXTENSIONS),
        max_bytes=settings.MAX_UPLOAD_BYTES,
    )


def build_update_document_field_interactor() -> UpdateDocumentFieldInteractor:
    return UpdateDocumentFieldInteractor(
        thread_storage=InMemoryScrutinyThreadStorage(),
        catalog_service=get_service_adapter().catalog_service,
        scrutiny_today=settings.SCRUTINY_TODAY,
    )


def build_confirm_document_fields_interactor() -> ConfirmDocumentFieldsInteractor:
    return ConfirmDocumentFieldsInteractor(
        thread_storage=InMemoryScrutinyThreadStorage()
    )


def build_resolve_check_interactor() -> ResolveCheckInteractor:
    return ResolveCheckInteractor(thread_storage=InMemoryScrutinyThreadStorage())


def build_retry_issuer_verification_interactor() -> RetryIssuerVerificationInteractor:
    return RetryIssuerVerificationInteractor(
        thread_storage=InMemoryScrutinyThreadStorage(),
        catalog_service=get_service_adapter().catalog_service,
        consultation=build_issuer_consultation(),
    )


def build_issuer_consultation() -> IssuerConsultation:
    service_adapter = get_service_adapter()
    return IssuerConsultation(
        catalog_service=service_adapter.catalog_service,
        verification_service=service_adapter.verification_service,
    )


def build_update_service_overrides_interactor() -> UpdateServiceOverridesInteractor:
    return UpdateServiceOverridesInteractor(
        thread_storage=InMemoryScrutinyThreadStorage()
    )


def build_get_chain_of_title_interactor() -> GetChainOfTitleInteractor:
    return GetChainOfTitleInteractor(thread_storage=InMemoryScrutinyThreadStorage())


def build_get_scrutiny_note_interactor() -> GetScrutinyNoteInteractor:
    return GetScrutinyNoteInteractor(
        thread_storage=InMemoryScrutinyThreadStorage(),
        catalog_service=get_service_adapter().catalog_service,
    )


def build_analyze_thread_interactor() -> AnalyzeThreadInteractor:
    thread_storage = InMemoryScrutinyThreadStorage()
    service_adapter = get_service_adapter()
    return AnalyzeThreadInteractor(
        thread_storage=thread_storage,
        analyze_document_interactor=AnalyzeDocumentInteractor(
            thread_storage=thread_storage,
            catalog_service=service_adapter.catalog_service,
            extraction_service=service_adapter.extraction_service,
            consultation=build_issuer_consultation(),
            scrutiny_today=settings.SCRUTINY_TODAY,
            segment_bundle_interactor=SegmentBundleInteractor(
                thread_storage=thread_storage
            ),
        ),
        failure_reporter=LoggingFailureReporter(),
        ownership_report_interactor=GetOwnershipReportInteractor(
            thread_storage=thread_storage
        ),
    )
