from document_scrutiny.domain.chain_of_title.chain_of_title import ChainOfTitle
from document_scrutiny.domain.chain_of_title.ownership_report import OwnershipReport
from document_scrutiny.domain.chain_of_title.thread_deeds import ThreadDeeds
from document_scrutiny.dtos.ownership_report_dtos import (
    OwnershipReportDTO,
    OwnershipReportRequestDTO,
)
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class GetOwnershipReportInteractor:
    """Who owns this land, how they came to, and what the officer still has to chase."""

    def __init__(self, thread_storage: ScrutinyThreadStorageInterface):
        self.thread_storage = thread_storage

    def get_ownership_report(
        self, request: OwnershipReportRequestDTO
    ) -> OwnershipReportDTO:
        thread = self.thread_storage.get_thread(thread_id=request.thread_id)
        deeds = ThreadDeeds.collect(documents=thread.documents)
        return OwnershipReport.compose(
            thread_id=thread.thread_id,
            deeds=deeds,
            chain=ChainOfTitle.validate(deeds=deeds),
        )
