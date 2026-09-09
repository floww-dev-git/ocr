from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.constants.pan_holder_types import PanFormatState
from document_scrutiny.domain.pan_format import PanFormat
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.pan_format_dtos import PanFormatDTO

PAN_FORMAT_CHECK_KEY = "pan-format"

_TITLES_BY_STATE = {
    PanFormatState.MALFORMED.value: "PAN is not a valid PAN",
    PanFormatState.UNRECOGNISED_HOLDER_TYPE.value: "PAN holder type is not recognised",
    PanFormatState.RECOGNISED.value: "PAN structure is valid",
}
_STATUSES_BY_STATE = {
    PanFormatState.MALFORMED.value: CheckStatus.FAIL.value,
    PanFormatState.UNRECOGNISED_HOLDER_TYPE.value: CheckStatus.WARN.value,
    PanFormatState.RECOGNISED.value: CheckStatus.PASS.value,
}


class PanFormatCheck:
    @classmethod
    def build(cls, document_id: str, field_key: str, pan: str) -> CheckDTO:
        pan_format = PanFormat.inspect(pan=pan)
        return CheckDTO(
            check_id=f"{document_id}:{PAN_FORMAT_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=_TITLES_BY_STATE[pan_format.state],
            status=_STATUSES_BY_STATE[pan_format.state],
            detail=cls._detail(pan_format=pan_format),
            field_key=field_key,
        )

    @staticmethod
    def _detail(pan_format: PanFormatDTO) -> str:
        if pan_format.state == PanFormatState.MALFORMED.value:
            return str(pan_format.rejection_reason)
        if pan_format.state == PanFormatState.UNRECOGNISED_HOLDER_TYPE.value:
            return (
                f"The fourth character {pan_format.holder_type_code} is not an "
                "issued holder-type code."
            )
        return f"Reads as a valid PAN. Holder type: {pan_format.holder_type_label}."
