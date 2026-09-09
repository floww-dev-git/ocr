from document_scrutiny.constants.aadhaar_format_constants import AadhaarFormatState
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.aadhaar_format import AadhaarFormat
from document_scrutiny.dtos.check_dtos import CheckDTO

AADHAAR_FORMAT_CHECK_KEY = "aadhaar-format"
RECOGNISED_DETAIL = "Reads as a twelve-digit Aadhaar number."

_TITLES_BY_STATE = {
    AadhaarFormatState.MALFORMED.value: "Aadhaar number is not a valid Aadhaar",
    AadhaarFormatState.CHECKSUM_FAILED.value: "Aadhaar number fails its checksum",
    AadhaarFormatState.RECOGNISED.value: "Aadhaar number structure is valid",
}
_STATUSES_BY_STATE = {
    AadhaarFormatState.MALFORMED.value: CheckStatus.FAIL.value,
    AadhaarFormatState.CHECKSUM_FAILED.value: CheckStatus.FAIL.value,
    AadhaarFormatState.RECOGNISED.value: CheckStatus.PASS.value,
}


class AadhaarFormatCheck:
    @classmethod
    def build(
        cls,
        document_id: str,
        field_key: str,
        aadhaar_number: str,
        enforce_checksum: bool = False,
    ) -> CheckDTO:
        aadhaar_format = AadhaarFormat.inspect(
            aadhaar_number=aadhaar_number, verify_checksum=enforce_checksum
        )
        return CheckDTO(
            check_id=f"{document_id}:{AADHAAR_FORMAT_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=_TITLES_BY_STATE[aadhaar_format.state],
            status=_STATUSES_BY_STATE[aadhaar_format.state],
            # The number itself is never echoed: this detail is copied into the
            # scrutiny note, and the officer already has the value on the card.
            detail=str(aadhaar_format.rejection_reason or RECOGNISED_DETAIL),
            field_key=field_key,
        )
