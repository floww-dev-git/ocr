from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.internal_consistency_check import (
    INTERNAL_CONSISTENCY_CHECK_KEY,
    InternalConsistencyCheck,
)

DOCUMENT_ID = "document_1"
SCRUTINY_TODAY = "2026-09-07"


def build(dob):
    return InternalConsistencyCheck.build(
        document_id=DOCUMENT_ID, date_of_birth=dob, scrutiny_today=SCRUTINY_TODAY
    )


class TestInternalConsistencyCheck:
    def test_a_plausible_date_of_birth_passes(self):
        check = build("1990-06-15")
        assert check is not None
        assert check.check_id == f"{DOCUMENT_ID}:{INTERNAL_CONSISTENCY_CHECK_KEY}"
        assert check.group == CheckGroup.RULE.value
        assert check.status == CheckStatus.PASS.value
        assert "15-06-1990" in check.detail

    def test_a_future_date_of_birth_fails(self):
        # Arrange — a card cannot have been born after the day it is scrutinised
        check = build("2035-01-02")
        assert check.status == CheckStatus.FAIL.value
        assert "future" in check.title.lower()

    def test_an_implausibly_old_date_of_birth_fails(self):
        check = build("1850-06-15")
        assert check.status == CheckStatus.FAIL.value
        assert "old" in check.title.lower()

    def test_a_year_only_date_warns_to_confirm_the_full_date(self):
        # Arrange — the reader normalises a year-only DOB to 01-01 and flags it
        check = build("1990-01-01")
        assert check.status == CheckStatus.WARN.value
        assert "year-only" in check.title.lower()

    def test_an_unreadable_date_warns_rather_than_passing(self):
        check = build("not-a-date")
        assert check.status == CheckStatus.WARN.value
        assert "could not be read" in check.title.lower()

    def test_no_date_of_birth_produces_no_check(self):
        # A document type that carries no date of birth is not judged here.
        assert build(None) is None
        assert build("") is None

    def test_the_day_before_scrutiny_is_still_plausible(self):
        # Arrange — a boundary: a birth on the scrutiny day itself is not future
        check = build(SCRUTINY_TODAY)
        assert check.status in {CheckStatus.PASS.value, CheckStatus.WARN.value}
        assert check.status != CheckStatus.FAIL.value
