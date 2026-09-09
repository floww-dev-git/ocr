from document_scrutiny.domain.chain_of_title.chain_of_title import ChainOfTitle
from document_scrutiny.domain.chain_of_title.thread_deeds import ThreadDeeds
from document_scrutiny.dtos.chain_dtos import ChainOfTitleDTO, ChainOfTitleRequestDTO
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)


class GetChainOfTitleInteractor:
    """Traces title across every registered deed attached to one thread.

    The deeds may have arrived as separate files or as one bundle that was segmented
    into several; by this point the difference no longer matters, because each is a
    document in its own right carrying its own record.
    """

    def __init__(self, thread_storage: ScrutinyThreadStorageInterface):
        self.thread_storage = thread_storage

    def get_chain_of_title(
        self, request: ChainOfTitleRequestDTO
    ) -> ChainOfTitleDTO:
        thread = self.thread_storage.get_thread(thread_id=request.thread_id)
        return ChainOfTitle.validate(
            deeds=ThreadDeeds.collect(documents=thread.documents)
        )
