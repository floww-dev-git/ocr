import pytest

from document_scrutiny.constants.enums import CheckStatus
from document_scrutiny.constants.validity_constants import (
    EXPIRING_SOON_DAYS,
    ValidityState,
)
from document_scrutiny.domain.comparison_rules.validity_window import ValidityWindow
from document_scrutiny.domain.validity_check import ValidityCheck

SCRUTINY_TODAY = "2026-09-07"
DOCUMENT_ID = "document_1"


class TestValidityWindow:
    def test_a_date_well_ahead_is_valid(self):
        # Arrange — the seeded licence runs to 2035
        # Act
        window = ValidityWindow.inspect(
            valid_until="2035-06-30", scrutiny_today=SCRUTINY_TODAY
        )

        # Assert
        assert window.state == ValidityState.VALID.value
        assert window.days_remaining > EXPIRING_SOON_DAYS

    def test_a_date_already_past_has_lapsed(self):
        # Act
        window = ValidityWindow.inspect(
            valid_until="2021-11-01", scrutiny_today=SCRUTINY_TODAY
        )

        # Assert
        assert window.state == ValidityState.LAPSED.value
        assert window.days_remaining < 0

    def test_expiring_today_has_not_lapsed_yet(self):
        # Arrange — a document is in force on its last day
        # Act
        window = ValidityWindow.inspect(
            valid_until=SCRUTINY_TODAY, scrutiny_today=SCRUTINY_TODAY
        )

        # Assert
        assert window.state == ValidityState.EXPIRING_SOON.value
        assert window.days_remaining == 0

    def test_expiring_the_day_before_has_lapsed(self):
        # Act
        window = ValidityWindow.inspect(
            valid_until="2026-09-06", scrutiny_today=SCRUTINY_TODAY
        )

        # Assert
        assert window.state == ValidityState.LAPSED.value
        assert window.days_remaining == -1

    def test_exactly_on_the_warning_horizon_still_warns(self):
        # Arrange — 180 days after 2026-09-07 is 2027-03-06
        # Act
        window = ValidityWindow.inspect(
            valid_until="2027-03-06", scrutiny_today=SCRUTINY_TODAY
        )

        # Assert
        assert window.days_remaining == EXPIRING_SOON_DAYS
        assert window.state == ValidityState.EXPIRING_SOON.value

    def test_one_day_past_the_warning_horizon_passes(self):
        # Act
        window = ValidityWindow.inspect(
            valid_until="2027-03-07", scrutiny_today=SCRUTINY_TODAY
        )

        # Assert
        assert window.days_remaining == EXPIRING_SOON_DAYS + 1
        assert window.state == ValidityState.VALID.value

    @pytest.mark.parametrize(
        "valid_until", [None, "", "   ", "30-06-2035", "next Tuesday", "2035-13-45"]
    )
    def test_a_date_that_could_not_be_read_says_so_rather_than_passing(
        self, valid_until
    ):
        # Arrange — reporting "valid" about a date nobody read is the worst answer
        # Act
        window = ValidityWindow.inspect(
            valid_until=valid_until, scrutiny_today=SCRUTINY_TODAY
        )

        # Assert
        assert window.state == ValidityState.UNREADABLE.value
        assert window.days_remaining is None

    def test_a_scrutiny_date_that_could_not_be_read_says_so_too(self):
        # Act
        window = ValidityWindow.inspect(
            valid_until="2035-06-30", scrutiny_today="not-a-date"
        )

        # Assert
        assert window.state == ValidityState.UNREADABLE.value


class TestValidityCheck:
    def _build(self, valid_until: str):
        return ValidityCheck.build(
            document_id=DOCUMENT_ID,
            field_key="validUpto",
            valid_until=valid_until,
            scrutiny_today=SCRUTINY_TODAY,
        )

    def test_a_valid_document_passes_and_names_the_date(self):
        # Act
        check = self._build("2035-06-30")

        # Assert
        assert check.status == CheckStatus.PASS.value
        assert check.title == "Valid"
        assert check.detail == "Valid until 30-06-2035."
        assert check.check_id == f"{DOCUMENT_ID}:validity"
        assert check.field_key == "validUpto"

    def test_an_expired_document_fails_and_names_the_date(self):
        # Act
        check = self._build("2021-11-01")

        # Assert
        assert check.status == CheckStatus.FAIL.value
        assert check.title == "Document has expired"
        assert check.detail == "Expired on 01-11-2021."

    def test_a_document_expiring_soon_warns_and_counts_the_days(self):
        # Act
        check = self._build("2026-10-01")

        # Assert
        assert check.status == CheckStatus.WARN.value
        assert check.title == "Expires soon"
        assert "24 days from today" in check.detail
        assert "Ask for a renewal" in check.detail

    def test_an_unreadable_date_warns_rather_than_passing_or_failing(self):
        # Act
        check = self._build("")

        # Assert
        assert check.status == CheckStatus.WARN.value
        assert "could not be read" in check.detail
