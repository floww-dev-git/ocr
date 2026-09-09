from document_catalog.app_interfaces.catalog_service_interface import (
    CatalogServiceInterface,
)
from document_scrutiny.domain.scrutiny_note import ScrutinyNote
from document_scrutiny.domain.scrutiny_summary import ScrutinySummary
from document_scrutiny.dtos.note_dtos import ScrutinyNoteDTO, ScrutinyNoteRequestDTO
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class GetScrutinyNoteInteractor:
    def __init__(
        self,
        thread_storage: ScrutinyThreadStorageInterface,
        catalog_service: CatalogServiceInterface,
    ):
        self.thread_storage = thread_storage
        self.catalog_service = catalog_service

    def get_note(self, request: ScrutinyNoteRequestDTO) -> ScrutinyNoteDTO:
        thread = self.thread_storage.get_thread(thread_id=request.thread_id)
        application = self.catalog_service.get_application(
            application_id=thread.application_id
        )
        return ScrutinyNoteDTO(
            thread_id=thread.thread_id,
            text=ScrutinyNote.compose(
                application=application,
                documents=thread.documents,
                summary=ScrutinySummary.summarise(thread.documents),
            ),
        )
