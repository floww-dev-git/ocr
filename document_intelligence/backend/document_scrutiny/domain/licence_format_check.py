from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.licence_format_constants import LicenceFormatState
from document_scrutiny.domain.licence_format import LicenceFormat
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.licence_format_dtos import LicenceFormatDTO

LICENCE_FORMAT_CHECK_KEY = "licence-format"

_TITLES_BY_STATE = {
    LicenceFormatState.MALFORMED.value: "Licence number is not a valid licence number",
    LicenceFormatState.IMPLAUSIBLE_YEAR.value: "Licence year of issue is not plausible",
    LicenceFormatState.RECOGNISED.value: "Licence number structure is valid",
}
_STATUSES_BY_STATE = {
    LicenceFormatState.MALFORMED.value: CheckStatus.FAIL.value,
    LicenceFormatState.IMPLAUSIBLE_YEAR.value: CheckStatus.WARN.value,
    LicenceFormatState.RECOGNISED.value: CheckStatus.PASS.value,
}


class LicenceFormatCheck:
    @classmethod
    def build(cls, document_id: str, field_key: str, licence_number: str) -> CheckDTO:
        licence_format = LicenceFormat.inspect(licence_number=licence_number)
        return CheckDTO(
            check_id=f"{document_id}:{LICENCE_FORMAT_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=_TITLES_BY_STATE[licence_format.state],
            status=_STATUSES_BY_STATE[licence_format.state],
            detail=cls._detail(licence_format=licence_format),
            field_key=field_key,
        )

    @staticmethod
    def _detail(licence_format: LicenceFormatDTO) -> str:
        if licence_format.state == LicenceFormatState.MALFORMED.value:
            return str(licence_format.rejection_reason)
        if licence_format.state == LicenceFormatState.IMPLAUSIBLE_YEAR.value:
            return (
                f"The year of issue reads {licence_format.issue_year}, which is not "
                "a year a licence could have been issued in."
            )
        return (
            f"Reads as a valid licence number. Issued in "
            f"{licence_format.issue_year} by state {licence_format.state_code}."
        )
