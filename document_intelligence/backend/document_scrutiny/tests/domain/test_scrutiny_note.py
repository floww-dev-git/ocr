from document_scrutiny.constants.enums import (
    CheckGroup,
    CheckStatus,
    DocumentStage,
    DocumentStatus,
    ThreadStatus,
)
from document_scrutiny.domain.scrutiny_note import (
    FIT_TO_PROCEED_RECOMMENDATION,
    NO_RECOMMENDATION_YET,
    RAISE_SHORTFALL_RECOMMENDATION,
    ScrutinyNote,
)
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.summary_dtos import OpenItemDTO, ScrutinySummaryDTO
from document_scrutiny.tests.conftest import MISMATCH_APPLICATION_ID, get_seeded_application

DOCUMENT_ID = "document_1"


def build_document(
    checks=(), stage: str = DocumentStage.DONE.value
) -> DocumentStateDTO:
    return DocumentStateDTO(
        document_id=DOCUMENT_ID,
        filename="pan.jpg",
        file_format="jpg",
        file_size_bytes=1024,
        document_type_id="pan",
        document_type_label="PAN card",
        type_confidence=0.99,
        implemented=True,
        stage=stage,
        status=DocumentStatus.VERIFIED.value,
        confirmed=False,
        page_count=1,
        checks=checks,
    )


def build_summary(
    status_counts=None, open_items=(), thread_status=ThreadStatus.CLEAR.value
) -> ScrutinySummaryDTO:
    return ScrutinySummaryDTO(
        thread_status=thread_status,
        document_count=1,
        confirmed_document_count=0,
        status_counts=status_counts or {},
        open_items=open_items,
    )


class TestScrutinyNote:
    def test_the_note_opens_with_the_application_it_belongs_to(self):
        application = get_seeded_application(MISMATCH_APPLICATION_ID)

        note = ScrutinyNote.compose(
            application=application,
            documents=(build_document(),),
            summary=build_summary(),
        )

        assert note.splitlines()[0] == f"Scrutiny note for {MISMATCH_APPLICATION_ID}"

    def test_the_note_describes_the_application_on_record(self):
        application = get_seeded_application(MISMATCH_APPLICATION_ID)

        note = ScrutinyNote.compose(
            application=application,
            documents=(build_document(),),
            summary=build_summary(),
        )

        assert application.field_values["applicantName"] in note
        assert application.field_values["village"] in note

    def test_only_documents_that_finished_are_counted_as_read(self):
        note = ScrutinyNote.compose(
            application=get_seeded_application(MISMATCH_APPLICATION_ID),
            documents=(
                build_document(),
                build_document(stage=DocumentStage.EXTRACTING.value),
            ),
            summary=build_summary(),
        )

        assert "Documents read: 1" in note

    def test_the_note_counts_the_checks_by_outcome(self):
        note = ScrutinyNote.compose(
            application=get_seeded_application(MISMATCH_APPLICATION_ID),
            documents=(build_document(),),
            summary=build_summary(
                status_counts={
                    CheckStatus.PASS.value: 7,
                    CheckStatus.WARN.value: 2,
                    CheckStatus.FAIL.value: 0,
                    CheckStatus.UNAVAILABLE.value: 0,
                }
            ),
        )

        assert "Checks: 7 passed, 2 warnings, 0 failed, 0 unavailable" in note

    def test_every_open_item_is_spelled_out_with_the_reason_behind_it(self):
        check = CheckDTO(
            check_id=f"{DOCUMENT_ID}:name",
            document_id=DOCUMENT_ID,
            group=CheckGroup.RULE.value,
            title="Name matches application",
            status=CheckStatus.WARN.value,
            detail="Read SIDDIQI, application says Siddiqui.",
        )

        note = ScrutinyNote.compose(
            application=get_seeded_application(MISMATCH_APPLICATION_ID),
            documents=(build_document(checks=(check,)),),
            summary=build_summary(
                thread_status=ThreadStatus.ATTENTION.value,
                open_items=(
                    OpenItemDTO(
                        document_id=DOCUMENT_ID,
                        check_id=check.check_id,
                        text="PAN card: Name matches application",
                    ),
                ),
            ),
        )

        assert (
            "Open: PAN card: Name matches application. "
            "Read SIDDIQI, application says Siddiqui." in note
        )

    def test_an_application_with_open_items_is_not_recommended_for_sanction(self):
        note = ScrutinyNote.compose(
            application=get_seeded_application(MISMATCH_APPLICATION_ID),
            documents=(build_document(),),
            summary=build_summary(
                thread_status=ThreadStatus.ATTENTION.value,
                open_items=(
                    OpenItemDTO(
                        document_id=DOCUMENT_ID,
                        check_id=f"{DOCUMENT_ID}:name",
                        text="PAN card: Name matches application",
                    ),
                ),
            ),
        )

        assert f"Recommendation: {RAISE_SHORTFALL_RECOMMENDATION}" in note

    def test_a_thread_where_nothing_was_read_recommends_nothing(self):
        note = ScrutinyNote.compose(
            application=get_seeded_application(MISMATCH_APPLICATION_ID),
            documents=(),
            summary=build_summary(thread_status=ThreadStatus.NEW.value),
        )

        assert f"Recommendation: {NO_RECOMMENDATION_YET}" in note
        assert FIT_TO_PROCEED_RECOMMENDATION not in note

    def test_a_thread_still_being_read_recommends_nothing_yet(self):
        note = ScrutinyNote.compose(
            application=get_seeded_application(MISMATCH_APPLICATION_ID),
            documents=(build_document(stage=DocumentStage.VERIFYING.value),),
            summary=build_summary(
                thread_status=ThreadStatus.RUNNING.value,
                status_counts={CheckStatus.PASS.value: 8},
            ),
        )

        assert f"Recommendation: {NO_RECOMMENDATION_YET}" in note
        assert FIT_TO_PROCEED_RECOMMENDATION not in note

    def test_a_document_still_being_read_does_not_count_as_read(self):
        note = ScrutinyNote.compose(
            application=get_seeded_application(MISMATCH_APPLICATION_ID),
            documents=(build_document(stage=DocumentStage.VERIFYING.value),),
            summary=build_summary(thread_status=ThreadStatus.RUNNING.value),
        )

        assert "Documents read: 0" in note

    def test_an_application_with_nothing_open_is_fit_to_proceed(self):
        note = ScrutinyNote.compose(
            application=get_seeded_application(MISMATCH_APPLICATION_ID),
            documents=(build_document(),),
            summary=build_summary(),
        )

        assert f"Recommendation: {FIT_TO_PROCEED_RECOMMENDATION}" in note
