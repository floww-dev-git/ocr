from typing import Any, Mapping, Optional, Tuple

from document_verification.constants.verification_constants import (
    DisagreeingField,
    IssuerOutcome,
    SarathiStatus,
)

_OUTCOMES_BY_STATUS = {
    SarathiStatus.NOT_FOUND.value: IssuerOutcome.NO_RECORD.value,
    SarathiStatus.NOT_MATCHED.value: IssuerOutcome.NOT_MATCHED.value,
}


class SarathiAnswerReader:
    """Reads what the Transport Department said about a licence.

    An active licence whose holder details do not line up is a partial match, not a
    confirmation: the department is vouching for the licence, not for the
    application form it was compared against.
    """

    @classmethod
    def read(cls, body: Mapping[str, Any]) -> Tuple[Optional[str], Tuple[str, ...]]:
        status = body.get("status")
        settled_outcome = _OUTCOMES_BY_STATUS.get(status)
        if settled_outcome is not None:
            return settled_outcome, ()
        if status != SarathiStatus.ACTIVE.value:
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
        # None means the department was not asked, which is not a disagreement.
        if body.get("dobMatch") is False:
            disagreeing.append(DisagreeingField.DATE_OF_BIRTH.value)
        return tuple(disagreeing)
