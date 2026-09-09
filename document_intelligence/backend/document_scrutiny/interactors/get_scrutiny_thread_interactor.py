from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class GetScrutinyThreadInteractor:
    def __init__(self, thread_storage: ScrutinyThreadStorageInterface):
        self.thread_storage = thread_storage

    def get_thread(self, thread_id: str) -> ScrutinyThreadDTO:
        return self.thread_storage.get_thread(thread_id=thread_id)
