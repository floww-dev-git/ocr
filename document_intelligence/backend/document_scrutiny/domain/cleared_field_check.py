from document_catalog.dtos.catalog_dtos import FieldSpecDTO
from document_scrutiny.constants.comparable_application_fields import (
    CHECK_KEYS_BY_APPLICATION_FIELD,
)
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.dtos.check_dtos import CheckDTO

CLEARED_FIELD_DETAIL = (
    "The officer cleared this value. Verify it against the original document "
    "and either enter it or record why it cannot be read."
)


class ClearedFieldCheck:
    """A field the officer emptied on purpose.

    An unread field produces no check at all, so that a bad scan does not bury
    the officer in failures it caused itself. A field the officer *cleared* is
    the opposite: a deliberate statement that the value could not be confirmed,
    and it has to stay on the worklist rather than quietly removing the
    disagreement that was there before.
    """

    @staticmethod
    def build(document_id: str, field_spec: FieldSpecDTO) -> CheckDTO:
        check_key = CHECK_KEYS_BY_APPLICATION_FIELD[field_spec.application_field_key]
        return CheckDTO(
            check_id=f"{document_id}:{check_key}",
            document_id=document_id,
            group=CheckGroup.RULE.value,
            title=f"{field_spec.label} was cleared by the officer",
            status=CheckStatus.WARN.value,
            detail=CLEARED_FIELD_DETAIL,
            field_key=field_spec.key,
        )
