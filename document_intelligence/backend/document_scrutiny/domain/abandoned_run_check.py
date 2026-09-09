from document_scrutiny.constants.analysis_constants import ABANDONED_RUN_CHECK_KEY
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.dtos.check_dtos import CheckDTO

ABANDONED_RUN_TITLE = "Reading this document did not finish"
ABANDONED_RUN_DETAIL = (
    "The run stopped before this document was fully read, so the checks below "
    "may be incomplete. Run the analysis again."
)


class AbandonedRunCheck:
    """Marks a document whose run stopped part way through.

    The document is recorded as finished so the thread can settle, but it carries
    a warning saying why, rather than presenting a partial read as a completed
    one. Same shape as the unsupported-document warning: settle the stage, keep
    the reason visible.
    """

    @staticmethod
    def build(document_id: str) -> CheckDTO:
        return CheckDTO(
            check_id=f"{document_id}:{ABANDONED_RUN_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=ABANDONED_RUN_TITLE,
            status=CheckStatus.WARN.value,
            detail=ABANDONED_RUN_DETAIL,
        )
