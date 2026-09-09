from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.issuer_check_constants import ISSUER_CHECK_KEY
from document_scrutiny.domain.document_verdict import DocumentVerdict
from document_scrutiny.domain.manual_verification_check import ManualVerificationCheck
from document_scrutiny.domain.open_check import is_open

DOCUMENT_ID = "document_1"
IRRIGATION_NOC_LABEL = "Irrigation NOC"


def build() -> object:
    return ManualVerificationCheck.build(
        document_id=DOCUMENT_ID, document_type_label=IRRIGATION_NOC_LABEL
    )


class TestManualVerificationCheck:
    def test_it_names_the_document_type_so_the_officer_knows_what_was_not_asked(self):
        # Act
        check = build()

        # Assert
        assert check.title == f"No department interface for this {IRRIGATION_NOC_LABEL}"
        assert "does not publish a verification interface" in check.detail
        assert "mark it verified by hand" in check.detail

    def test_it_takes_the_place_of_a_departments_answer(self):
        # Act
        check = build()

        # Assert — one external check per document, whether or not a department
        # could be asked, so nothing downstream has to special-case its absence
        assert check.check_id == f"{DOCUMENT_ID}:{ISSUER_CHECK_KEY}"
        assert check.group == CheckGroup.EXTERNAL.value

    def test_it_carries_no_issuer_call_because_no_call_was_made(self):
        # Act
        check = build()

        # Assert
        assert check.issuer_call is None

    def test_it_is_for_information_and_not_an_open_item(self):
        # Act
        check = build()

        # Assert — an absent interface is not something the applicant can fix, so it
        # is not held against them; only the officer's own verification closes it
        assert check.status == CheckStatus.INFO.value
        assert is_open(check) is False

    def test_a_document_carrying_only_this_check_still_reads_as_verified(self):
        # Act
        verdict = DocumentVerdict.derive(stage="done", checks=[build()])

        # Assert
        assert verdict == "verified"

    def test_the_officer_can_still_record_having_verified_it_by_hand(self):
        # Arrange
        import dataclasses

        # Act
        resolved = dataclasses.replace(build(), manual=True)

        # Assert — the machine's verdict is untouched by the officer's disposition
        assert resolved.manual is True
        assert resolved.status == CheckStatus.INFO.value
        assert resolved.title == f"No department interface for this {IRRIGATION_NOC_LABEL}"
