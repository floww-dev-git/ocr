from typing import Mapping, Optional, Tuple

import pytest

from document_catalog.dtos.catalog_dtos import ApplicationDTO
from document_catalog.storages.reference_data.application_specs import APPLICATION_SPECS
from document_catalog.storages.reference_data.identity_document_specs import (
    AADHAAR_SPEC,
    PAN_SPEC,
)
from document_scrutiny.dtos.document_dtos import DocumentStateDTO, FieldValueDTO
from document_scrutiny.dtos.run_checks_dtos import RunDocumentChecksRequestDTO

CLEAN_APPLICATION_ID = "BN/2026/0421"
SECOND_APPLICATION_ID = "BN/2026/0398"
MISMATCH_APPLICATION_ID = "BN/2026/0377"
DOCUMENT_ID = "document_1"
# The date the demo is pinned to, matching settings.SCRUTINY_TODAY.
SCRUTINY_TODAY = "2026-09-07"

ALL_STRUCTURE_PRESENT: Mapping[str, bool] = {
    "photo": True,
    "signature": True,
    "hologram": True,
}


def get_seeded_application(application_id: str) -> ApplicationDTO:
    return next(
        application
        for application in APPLICATION_SPECS
        if application.application_id == application_id
    )


def build_pan_field_values(
    name: str,
    parent_name: str,
    date_of_birth: str,
    pan: str,
) -> Tuple[FieldValueDTO, ...]:
    return (
        FieldValueDTO(key="name", value=name, confidence=0.98),
        FieldValueDTO(key="parentName", value=parent_name, confidence=0.96),
        FieldValueDTO(key="dob", value=date_of_birth, confidence=0.99),
        FieldValueDTO(key="pan", value=pan, confidence=0.99),
    )


AADHAAR_STRUCTURE_PRESENT: Mapping[str, bool] = {
    "photo": True,
    "qr": True,
    "emblem": True,
}


def build_aadhaar_field_values(
    name: str,
    date_of_birth: str,
    gender: str,
    aadhaar_number: str,
    address: str,
) -> Tuple[FieldValueDTO, ...]:
    return (
        FieldValueDTO(key="name", value=name, confidence=0.97),
        FieldValueDTO(key="dob", value=date_of_birth, confidence=0.99),
        FieldValueDTO(key="gender", value=gender, confidence=0.99),
        FieldValueDTO(key="aadhaarNo", value=aadhaar_number, confidence=0.99),
        FieldValueDTO(key="address", value=address, confidence=0.93),
    )


def build_aadhaar_checks_request(
    application_id: str = CLEAN_APPLICATION_ID,
    field_values: Optional[Tuple[FieldValueDTO, ...]] = None,
    structure_findings: Optional[Mapping[str, bool]] = None,
) -> RunDocumentChecksRequestDTO:
    application = get_seeded_application(application_id)
    if field_values is None:
        field_values = build_aadhaar_field_values(
            name=application.field_values["applicantName"],
            date_of_birth=application.field_values["dob"],
            gender=application.field_values["gender"],
            aadhaar_number=application.field_values["aadhaarNo"],
            address=application.field_values["address"],
        )
    return RunDocumentChecksRequestDTO(
        document_id=DOCUMENT_ID,
        document_type=AADHAAR_SPEC,
        application=application,
        scrutiny_today=SCRUTINY_TODAY,
        field_values=field_values,
        structure_findings=dict(
            AADHAAR_STRUCTURE_PRESENT
            if structure_findings is None
            else structure_findings
        ),
    )


def build_pan_checks_request(
    application_id: str = CLEAN_APPLICATION_ID,
    field_values: Optional[Tuple[FieldValueDTO, ...]] = None,
    structure_findings: Optional[Mapping[str, bool]] = None,
) -> RunDocumentChecksRequestDTO:
    application = get_seeded_application(application_id)
    if field_values is None:
        field_values = build_pan_field_values(
            name=application.field_values["applicantName"].upper(),
            parent_name=application.field_values["parentName"].upper(),
            date_of_birth=application.field_values["dob"],
            pan=application.field_values["pan"],
        )
    return RunDocumentChecksRequestDTO(
        document_id=DOCUMENT_ID,
        document_type=PAN_SPEC,
        application=application,
        scrutiny_today=SCRUTINY_TODAY,
        field_values=field_values,
        structure_findings=dict(
            ALL_STRUCTURE_PRESENT if structure_findings is None else structure_findings
        ),
    )


def wire_document_memory(
    thread_storage,
    documents: Tuple[DocumentStateDTO, ...],
    application_id: str = MISMATCH_APPLICATION_ID,
    service_overrides: Optional[Mapping[str, str]] = None,
):
    """Makes an autospec thread storage remember what was written to it, so a
    summary read after an edit reflects that edit rather than stale state."""
    from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO

    state = {document.document_id: document for document in documents}
    overrides = dict(service_overrides or {})

    def _update_document(update_document):
        state[update_document.document.document_id] = update_document.document
        return update_document.document

    def _get_thread(thread_id):
        return ScrutinyThreadDTO(
            thread_id=thread_id,
            application_id=application_id,
            documents=tuple(state.values()),
            service_overrides=dict(overrides),
        )

    def _get_document(lookup):
        return state[lookup.document_id]

    thread_storage.update_document.side_effect = _update_document
    thread_storage.get_thread.side_effect = _get_thread
    thread_storage.get_document.side_effect = _get_document
    return state


@pytest.fixture(autouse=True)
def empty_thread_store():
    from document_scrutiny.storages.in_memory_scrutiny_thread_storage import (
        clear_scrutiny_threads,
    )

    clear_scrutiny_threads()
    yield
    clear_scrutiny_threads()


class ScrutinyStorageMock:
    @pytest.fixture
    def clean_application(self) -> ApplicationDTO:
        return get_seeded_application(CLEAN_APPLICATION_ID)

    @pytest.fixture
    def mismatch_application(self) -> ApplicationDTO:
        return get_seeded_application(MISMATCH_APPLICATION_ID)

    @pytest.fixture
    def catalog_service(self):
        """The real catalog. It is in-memory reference data with no I/O, so these
        tests deliberately read the same specs and applications production does
        rather than restating them in a mock. The dependency is injected so that
        choice is visible in the constructor instead of reached for at runtime."""
        from document_catalog.app_interfaces.catalog_service_interface import (
            CatalogServiceInterface,
        )

        return CatalogServiceInterface()

    @pytest.fixture
    def thread_storage(self):
        from unittest.mock import create_autospec

        from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
            ScrutinyThreadStorageInterface,
        )

        return create_autospec(ScrutinyThreadStorageInterface)

    @pytest.fixture
    def document_file_store(self):
        from unittest.mock import create_autospec

        from document_scrutiny.adapters.document_file_store_interface import (
            DocumentFileStoreInterface,
        )

        return create_autospec(DocumentFileStoreInterface)

    @pytest.fixture
    def segment_bundle_interactor(self, thread_storage):
        """The real one, over the same mocked storage. It writes children and closes
        the parent, which is behaviour worth exercising rather than stubbing out."""
        from document_scrutiny.interactors.segment_bundle_interactor import (
            SegmentBundleInteractor,
        )

        return SegmentBundleInteractor(thread_storage=thread_storage)
