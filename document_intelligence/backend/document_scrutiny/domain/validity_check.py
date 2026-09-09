from typing import Optional

from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.validity_constants import (
    VALIDITY_CHECK_KEY,
    ValidityState,
)
from document_scrutiny.domain.comparison_rules.validity_window import ValidityWindow
from document_scrutiny.domain.date_display import format_iso_date
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.validity_dtos import ValidityWindowDTO

UNREADABLE_TITLE = "Valid until could not be read"
UNREADABLE_DETAIL = (
    "The date this document runs to could not be read. Check the original before "
    "relying on it."
)

_TITLES_BY_STATE = {
    ValidityState.LAPSED.value: "Document has expired",
    ValidityState.EXPIRING_SOON.value: "Expires soon",
    ValidityState.VALID.value: "Valid",
    ValidityState.UNREADABLE.value: UNREADABLE_TITLE,
}
_STATUSES_BY_STATE = {
    ValidityState.LAPSED.value: CheckStatus.FAIL.value,
    ValidityState.EXPIRING_SOON.value: CheckStatus.WARN.value,
    ValidityState.VALID.value: CheckStatus.PASS.value,
    ValidityState.UNREADABLE.value: CheckStatus.WARN.value,
}


class ValidityCheck:
    """Whether the document is still in force on the day it is being scrutinised.

    Answerable from the document and the calendar alone, with nothing on the
    application to compare against.
    """

    @classmethod
    def build(
        cls,
        document_id: str,
        field_key: str,
        valid_until: str,
        scrutiny_today: str,
    ) -> CheckDTO:
        window = ValidityWindow.inspect(
            valid_until=valid_until, scrutiny_today=scrutiny_today
        )
        return CheckDTO(
            check_id=f"{document_id}:{VALIDITY_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=_TITLES_BY_STATE[window.state],
            status=_STATUSES_BY_STATE[window.state],
            detail=cls._detail(window=window, valid_until=valid_until),
            field_key=field_key,
        )

    @classmethod
    def _detail(cls, window: ValidityWindowDTO, valid_until: str) -> str:
        shown_date = format_iso_date(valid_until)
        if window.state == ValidityState.UNREADABLE.value:
            return UNREADABLE_DETAIL
        if window.state == ValidityState.LAPSED.value:
            return f"Expired on {shown_date}."
        if window.state == ValidityState.EXPIRING_SOON.value:
            return (
                f"Valid until {shown_date}, {cls._days(window)} days from today. "
                "Ask for a renewal if sanction is expected after that."
            )
        return f"Valid until {shown_date}."

    @staticmethod
    def _days(window: ValidityWindowDTO) -> Optional[int]:
        return window.days_remaining
