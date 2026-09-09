from typing import Any, Mapping, Optional, Tuple

from document_verification.constants.verification_constants import (
    DisagreeingField,
    IgrsStatus,
    IssuerOutcome,
)

_OUTCOMES_BY_STATUS = {
    IgrsStatus.NOT_FOUND.value: IssuerOutcome.NO_RECORD.value,
    IgrsStatus.NOT_MATCHED.value: IssuerOutcome.NOT_MATCHED.value,
}


class IgrsAnswerReader:
    """Reads what the registrar said about a deed.

    A deed that is registered but not to the person named on the paper is a partial
    match, not a confirmation: the register is vouching for the registration, and
    the discrepancy in who holds it is exactly what the officer needs to see.
    """

    @classmethod
    def read(cls, body: Mapping[str, Any]) -> Tuple[Optional[str], Tuple[str, ...]]:
        status = body.get("status")
        settled_outcome = _OUTCOMES_BY_STATUS.get(status)
        if settled_outcome is not None:
            return settled_outcome, ()
        if status != IgrsStatus.REGISTERED.value:
            return None, ()

        if body.get("nameMatch") is not True:
            return (
                IssuerOutcome.PARTIAL_MATCH.value,
                (DisagreeingField.NAME.value,),
            )
        return IssuerOutcome.CONFIRMED.value, ()
