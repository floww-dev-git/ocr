from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.cross_document_consistency_check import (
    CROSS_DOCUMENT_CHECK_KEY,
    CrossDocumentConsistencyCheck,
    SiblingName,
)

DOCUMENT_ID = "document_1"


def build(name, siblings):
    return CrossDocumentConsistencyCheck.build(
        document_id=DOCUMENT_ID, name=name, siblings=siblings
    )


class TestCrossDocumentConsistencyCheck:
    def test_matching_names_across_documents_pass(self):
        check = build(
            "Rithika Sharma", [SiblingName(document_type_label="PAN", name="Rithika Sharma")]
        )
        assert check is not None
        assert check.check_id == f"{DOCUMENT_ID}:{CROSS_DOCUMENT_CHECK_KEY}"
        assert check.group == CheckGroup.CROSS.value
        assert check.status == CheckStatus.PASS.value

    def test_disagreeing_names_warn_and_name_the_other_document(self):
        # Arrange — the Aadhaar and the PAN name different people
        check = build(
            "Rithika Sharma",
            [SiblingName(document_type_label="PAN", name="Vikram Anand Reddy")],
        )

        # Assert
        assert check.status == CheckStatus.WARN.value
        assert "Rithika Sharma" in check.detail
        assert "the PAN reads Vikram Anand Reddy" in check.detail

    def test_a_minor_spelling_difference_still_agrees(self):
        # Arrange — OCR noise between two documents is not a disagreement
        check = build(
            "Rithika Sharma", [SiblingName(document_type_label="PAN", name="RITHIKA  SHARMA")]
        )
        assert check.status == CheckStatus.PASS.value

    def test_no_siblings_produces_no_check(self):
        # The first identity document on a file has nothing to reconcile against.
        assert build("Rithika Sharma", []) is None

    def test_no_name_on_this_document_produces_no_check(self):
        assert build(None, [SiblingName(document_type_label="PAN", name="Rithika Sharma")]) is None
        assert build("", [SiblingName(document_type_label="PAN", name="Rithika Sharma")]) is None

    def test_a_sibling_with_no_name_is_ignored(self):
        # Arrange — a sibling document that carried no name cannot disagree
        check = build(
            "Rithika Sharma", [SiblingName(document_type_label="PAN", name="")]
        )
        # Nothing to compare against -> treated as agreement (no disagreement found)
        assert check.status == CheckStatus.PASS.value

    def test_one_agreeing_and_one_disagreeing_sibling_warns(self):
        check = build(
            "Rithika Sharma",
            [
                SiblingName(document_type_label="PAN", name="Rithika Sharma"),
                SiblingName(document_type_label="Driving licence", name="Someone Else"),
            ],
        )
        assert check.status == CheckStatus.WARN.value
        assert "the Driving licence reads Someone Else" in check.detail
        assert "the PAN" not in check.detail
