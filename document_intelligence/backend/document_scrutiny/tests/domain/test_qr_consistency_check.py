from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.qr_consistency_check import (
    QR_CONSISTENCY_CHECK_KEY,
    QrConsistencyCheck,
)

DOCUMENT_ID = "document_1"
CLEAN_QR = {
    "name": "Rithika Sharma",
    "aadhaarNo": "234567890124",
    "dob": "1990-06-15",
}
CLEAN_PRINT = {
    "name": "Rithika Sharma",
    "aadhaarNo": "234567890124",
    "dob": "1990-06-15",
}


def build(qr_fields, printed_values):
    return QrConsistencyCheck.build(
        document_id=DOCUMENT_ID, qr_fields=qr_fields, printed_values=printed_values
    )


class TestQrConsistencyCheck:
    def test_it_carries_a_stable_id_and_the_rule_group(self):
        check = build(CLEAN_QR, CLEAN_PRINT)
        assert check.check_id == f"{DOCUMENT_ID}:{QR_CONSISTENCY_CHECK_KEY}"
        assert check.group == CheckGroup.RULE.value

    def test_a_qr_that_agrees_with_the_print_passes(self):
        check = build(CLEAN_QR, CLEAN_PRINT)
        assert check.status == CheckStatus.PASS.value
        assert "match" in check.detail.lower()

    def test_a_qr_that_contradicts_the_printed_name_warns(self):
        # Arrange — the tamper case: print altered, QR left carrying the original
        printed = {**CLEAN_PRINT, "name": "Rithika Verma"}

        # Act
        check = build(CLEAN_QR, printed)

        # Assert — a needs-a-look integrity signal, not a hard fail
        assert check.status == CheckStatus.WARN.value
        assert "the name" in check.detail
        assert "verify it against the original" in check.detail

    def test_a_qr_that_contradicts_the_printed_number_warns(self):
        printed = {**CLEAN_PRINT, "aadhaarNo": "234567890125"}
        check = build(CLEAN_QR, printed)
        assert check.status == CheckStatus.WARN.value
        assert "the Aadhaar number" in check.detail

    def test_a_minor_name_spelling_difference_still_agrees(self):
        # Arrange — OCR case/spacing noise must not read as tamper
        printed = {**CLEAN_PRINT, "name": "RITHIKA  SHARMA"}
        check = build(CLEAN_QR, printed)
        assert check.status == CheckStatus.PASS.value

    def test_no_qr_is_reported_as_information_not_a_pass(self):
        check = build(None, CLEAN_PRINT)
        assert check.status == CheckStatus.INFO.value
        assert "No machine-readable QR" in check.detail

    def test_a_field_the_qr_does_not_carry_is_not_judged(self):
        # Arrange — QR carries only the number; print has a different name
        qr = {"aadhaarNo": "234567890124"}
        printed = {"name": "Someone Else", "aadhaarNo": "234567890124"}

        # Act
        check = build(qr, printed)

        # Assert — the number agrees and the name was not in the QR to compare
        assert check.status == CheckStatus.PASS.value
