from document_scrutiny.dtos.officer_action_dtos import UpdateServiceOverridesRequestDTO
from document_scrutiny.dtos.thread_dtos import (
    ScrutinyThreadDTO,
    UpdateServiceOverridesDTO,
)
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class UpdateServiceOverridesInteractor:
    """Demo control: forces a chosen answer out of an issuer service so the
    unreachable and mismatch paths can be shown on demand."""

    def __init__(self, thread_storage: ScrutinyThreadStorageInterface):
        self.thread_storage = thread_storage

    def update_overrides(
        self, request: UpdateServiceOverridesRequestDTO
    ) -> ScrutinyThreadDTO:
        self.thread_storage.get_thread(thread_id=request.thread_id)
        return self.thread_storage.update_service_overrides(
            update_overrides=UpdateServiceOverridesDTO(
                thread_id=request.thread_id,
                service_overrides=dict(request.service_overrides),
            )
        )
