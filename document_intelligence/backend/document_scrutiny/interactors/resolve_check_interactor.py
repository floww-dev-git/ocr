import dataclasses
from typing import Mapping, Optional, Tuple

from document_scrutiny.constants.enums import CheckResolution
from document_scrutiny.domain.officer_action_guard import OfficerActionGuard
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.officer_action_dtos import (
    CheckChangeDTO,
    ResolveCheckRequestDTO,
)
from document_scrutiny.exceptions.scrutiny_exceptions import (
    CheckNotFound,
    UnknownCheckResolution,
)
from document_scrutiny.interactors.thread_revision import ThreadRevision
from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
    ScrutinyThreadStorageInterface,
)

_FLAGS_BY_RESOLUTION: Mapping[str, str] = {
    CheckResolution.ACKNOWLEDGED.value: "acknowledged",
    CheckResolution.MANUAL.value: "manual",
    CheckResolution.REQUESTED.value: "requested",
}


class ResolveCheckInteractor:
    def __init__(self, thread_storage: ScrutinyThreadStorageInterface):
        self.thread_storage = thread_storage
        self.revision = ThreadRevision(thread_storage=thread_storage)

    def resolve_check(self, request: ResolveCheckRequestDTO) -> CheckChangeDTO:
        flag = self._read_flag(request.action)
        thread = self.thread_storage.get_thread(thread_id=request.thread_id)
        document, check = self._locate_check(
            documents=thread.documents,
            thread_id=request.thread_id,
            check_id=request.check_id,
        )
        OfficerActionGuard.check_document_is_not_being_read(document)
        # The officer's own reading of a check never rewrites its status or title:
        # the machine's verdict and the officer's disposition stay separable.
        resolved = dataclasses.replace(check, **{flag: True})
        saved, summary = self.revision.save_document(
            thread_id=request.thread_id,
            document=self._replace_check(document=document, resolved=resolved),
        )
        return CheckChangeDTO(check=resolved, document=saved, summary=summary)

    @staticmethod
    def _read_flag(action: str) -> str:
        flag: Optional[str] = _FLAGS_BY_RESOLUTION.get(action)
        if flag is None:
            raise UnknownCheckResolution(action=action)
        return flag

    @staticmethod
    def _locate_check(
        documents: Tuple[DocumentStateDTO, ...], thread_id: str, check_id: str
    ) -> Tuple[DocumentStateDTO, CheckDTO]:
        for document in documents:
            for check in document.checks:
                if check.check_id == check_id:
                    return document, check
        raise CheckNotFound(thread_id=thread_id, check_id=check_id)

    @staticmethod
    def _replace_check(
        document: DocumentStateDTO, resolved: CheckDTO
    ) -> DocumentStateDTO:
        return dataclasses.replace(
            document,
            checks=tuple(
                resolved if check.check_id == resolved.check_id else check
                for check in document.checks
            ),
        )
