from typing import Sequence

from document_scrutiny.constants.enums import CheckStatus, DocumentStage, DocumentStatus
from document_scrutiny.domain.open_check import is_open
from document_scrutiny.dtos.check_dtos import CheckDTO


class DocumentVerdict:
    @staticmethod
    def derive(stage: str, checks: Sequence[CheckDTO]) -> str:
        if stage != DocumentStage.DONE.value:
            return DocumentStatus.CHECKING.value

        open_statuses = {check.status for check in checks if is_open(check)}
        if CheckStatus.FAIL.value in open_statuses:
            return DocumentStatus.FAILED.value
        if CheckStatus.UNAVAILABLE.value in open_statuses:
            return DocumentStatus.UNAVAILABLE.value
        if open_statuses:
            return DocumentStatus.ATTENTION.value
        return DocumentStatus.VERIFIED.value
