from typing import Dict, List, Sequence

from document_catalog.dtos.catalog_dtos import ApplicationDTO
from document_scrutiny.constants.enums import CheckStatus, DocumentStage, ThreadStatus
from document_scrutiny.constants.note_application_fields import NoteApplicationField
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.summary_dtos import ScrutinySummaryDTO

NOT_SET = "not set"
UNKNOWN = "?"
RAISE_SHORTFALL_RECOMMENDATION = (
    "Raise shortfall for the items above before sanction"
)
FIT_TO_PROCEED_RECOMMENDATION = "Fit to proceed"
NO_RECOMMENDATION_YET = (
    "No recommendation yet, the documents have not all been read"
)

_UNSETTLED_THREAD_STATUSES = (
    ThreadStatus.NEW.value,
    ThreadStatus.RUNNING.value,
)


class ScrutinyNote:
    @classmethod
    def compose(
        cls,
        application: ApplicationDTO,
        documents: Sequence[DocumentStateDTO],
        summary: ScrutinySummaryDTO,
    ) -> str:
        lines = [
            f"Scrutiny note for {application.application_id}",
            cls._describe_application(application.field_values),
            f"Documents read: {cls._count_read(documents)}",
            cls._describe_checks(summary.status_counts),
        ]
        lines.extend(cls._describe_open_items(documents=documents, summary=summary))
        lines.append(f"Recommendation: {cls._recommend(summary)}")
        return "\n".join(lines)

    @staticmethod
    def _describe_application(field_values: Dict[str, str]) -> str:
        def read(field: NoteApplicationField, fallback: str = UNKNOWN) -> str:
            return field_values.get(field.value) or fallback

        village = read(NoteApplicationField.VILLAGE, "")
        location = f"survey {read(NoteApplicationField.SURVEY_NO)} plot {read(NoteApplicationField.PLOT_NO)}"
        return (
            f"Applicant {read(NoteApplicationField.APPLICANT_NAME, NOT_SET)}, "
            f"{read(NoteApplicationField.PROPOSED_USE, 'use ' + NOT_SET)}, "
            f"{read(NoteApplicationField.FLOORS, 'floors ' + NOT_SET)}, "
            f"{read(NoteApplicationField.HEIGHT_M)} m, "
            f"{location}{f', {village}' if village else ''}."
        )

    @staticmethod
    def _count_read(documents: Sequence[DocumentStateDTO]) -> int:
        return sum(
            1 for document in documents if document.stage == DocumentStage.DONE.value
        )

    @staticmethod
    def _describe_checks(status_counts: Dict[str, int]) -> str:
        return (
            f"Checks: {status_counts.get(CheckStatus.PASS.value, 0)} passed, "
            f"{status_counts.get(CheckStatus.WARN.value, 0)} warnings, "
            f"{status_counts.get(CheckStatus.FAIL.value, 0)} failed, "
            f"{status_counts.get(CheckStatus.UNAVAILABLE.value, 0)} unavailable"
        )

    @classmethod
    def _describe_open_items(
        cls,
        documents: Sequence[DocumentStateDTO],
        summary: ScrutinySummaryDTO,
    ) -> List[str]:
        checks_by_id = {
            check.check_id: check
            for document in documents
            for check in document.checks
        }
        lines = []
        for open_item in summary.open_items:
            check = checks_by_id.get(open_item.check_id)
            if check is None:
                continue
            lines.append(f"Open: {open_item.text}. {check.detail}")
        return lines

    @staticmethod
    def _recommend(summary: ScrutinySummaryDTO) -> str:
        # "Nothing is open" and "nothing was looked at" produce the same empty
        # open-item list, so the recommendation reads the thread's own state
        # instead. A note that recommends sanction over unread paper is worse
        # than a note that declines to recommend anything.
        if summary.thread_status in _UNSETTLED_THREAD_STATUSES:
            return NO_RECOMMENDATION_YET
        if summary.open_items:
            return RAISE_SHORTFALL_RECOMMENDATION
        return FIT_TO_PROCEED_RECOMMENDATION
