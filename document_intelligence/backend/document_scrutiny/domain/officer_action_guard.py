from document_scrutiny.constants.enums import DocumentStage
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.exceptions.scrutiny_exceptions import DocumentBusy

MID_RUN_STAGES = (
    DocumentStage.IDENTIFYING.value,
    DocumentStage.EXTRACTING.value,
    DocumentStage.CHECKING.value,
    DocumentStage.VERIFYING.value,
)


class OfficerActionGuard:
    """Refuses officer actions on a document that is still being read.

    The analyze run works from the document it read at the start and writes its
    own result back at each stage. An edit accepted in the middle of that would
    be reported to the officer as saved and then overwritten seconds later, with
    nothing left to show it ever happened. Being told to wait is honest; being
    told "saved" and silently losing it is not.
    """

    @staticmethod
    def check_document_is_not_being_read(document: DocumentStateDTO) -> None:
        if document.stage in MID_RUN_STAGES:
            raise DocumentBusy(
                document_id=document.document_id, stage=document.stage
            )
