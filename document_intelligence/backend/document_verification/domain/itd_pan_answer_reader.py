from typing import Any, Mapping, Optional, Tuple

from document_verification.constants.verification_constants import (
    DisagreeingField,
    IssuerOutcome,
    IssuerStatus,
)

_OUTCOMES_BY_STATUS = {
    IssuerStatus.NOT_FOUND.value: IssuerOutcome.NO_RECORD.value,
    IssuerStatus.NOT_MATCHED.value: IssuerOutcome.NOT_MATCHED.value,
}


class ItdPanAnswerReader:
    """Reads what the Income Tax Department's PAN service said.

    One reader per issuer: each department answers in its own vocabulary, and
    guessing across them is how a disagreement gets read as a confirmation.
    """

    @classmethod
    def read(cls, body: Mapping[str, Any]) -> Tuple[Optional[str], Tuple[str, ...]]:
        status = body.get("status")
        settled_outcome = _OUTCOMES_BY_STATUS.get(status)
        if settled_outcome is not None:
            return settled_outcome, ()
        if status != IssuerStatus.VALID.value:
            return None, ()

        disagreeing_fields = cls._collect_disagreeing_fields(body)
        if disagreeing_fields:
            return IssuerOutcome.PARTIAL_MATCH.value, disagreeing_fields
        return IssuerOutcome.CONFIRMED.value, ()

    @staticmethod
    def _collect_disagreeing_fields(body: Mapping[str, Any]) -> Tuple[str, ...]:
        disagreeing = []
        if body.get("nameMatch") is not True:
            disagreeing.append(DisagreeingField.NAME.value)
        if body.get("dobMatch") is False:
            disagreeing.append(DisagreeingField.DATE_OF_BIRTH.value)
        return tuple(disagreeing)
