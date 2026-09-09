from document_scrutiny.constants.analysis_constants import (
    UNCLASSIFIED_DOCUMENT_MESSAGE,
    UNCLASSIFIED_DOCUMENT_TYPE_ID,
    UNSUPPORTED_CHECK_KEY,
    UNSUPPORTED_TYPE_MESSAGE,
)
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.dtos.check_dtos import CheckDTO

UNCLASSIFIED_TITLE = "Document type could not be established"
UNCLASSIFIED_DETAIL = (
    "Nothing was read from this document. Attach a clearer copy, or set it aside and "
    "verify it against the original."
)
UNSUPPORTED_DETAIL = (
    "This system does not yet read {label}. Verify it against the original and mark "
    "this verified by hand, or set the document aside."
)


class UnsupportedTypeCheck:
    @classmethod
    def build(
        cls, document_id: str, document_type_id: str, document_type_label: str
    ) -> CheckDTO:
        unclassified = document_type_id == UNCLASSIFIED_DOCUMENT_TYPE_ID
        return CheckDTO(
            check_id=f"{document_id}:{UNSUPPORTED_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=(
                UNCLASSIFIED_TITLE
                if unclassified
                else f"{document_type_label} is not supported in this build"
            ),
            status=CheckStatus.WARN.value,
            detail=(
                UNCLASSIFIED_DETAIL
                if unclassified
                else UNSUPPORTED_DETAIL.format(label=document_type_label)
            ),
        )

    @staticmethod
    def build_message(
        document_type_id: str, document_type_label: str, filename: str
    ) -> str:
        if document_type_id == UNCLASSIFIED_DOCUMENT_TYPE_ID:
            return UNCLASSIFIED_DOCUMENT_MESSAGE.format(filename=filename)
        return UNSUPPORTED_TYPE_MESSAGE.format(label=document_type_label)
