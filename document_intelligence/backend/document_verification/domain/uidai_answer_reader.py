from typing import Any, Mapping, Optional, Tuple

from document_verification.constants.verification_constants import (
    ALL_UIDAI_DEMOGRAPHICS,
    IssuerOutcome,
    UidaiStatus,
)

_OUTCOMES_BY_STATUS = {
    UidaiStatus.NOT_FOUND.value: IssuerOutcome.NO_RECORD.value,
    UidaiStatus.NOT_MATCHED.value: IssuerOutcome.NOT_MATCHED.value,
}


class UidaiAnswerReader:
    """Reads what UIDAI's demographic authentication said.

    UIDAI reports which demographics agreed rather than a verdict, so anything it
    does not list is taken as disagreeing. A `matched` list that is absent
    altogether is unreadable rather than a silent full agreement: reading a missing
    field as consent is how an unverified card gets reported as confirmed.
    """

    @classmethod
    def read(cls, body: Mapping[str, Any]) -> Tuple[Optional[str], Tuple[str, ...]]:
        status = body.get("status")
        settled_outcome = _OUTCOMES_BY_STATUS.get(status)
        if settled_outcome is not None:
            return settled_outcome, ()
        if status != UidaiStatus.MATCHED.value:
            return None, ()

        matched = body.get("matched")
        if not isinstance(matched, list):
            return None, ()

        disagreeing = tuple(
            field for field in ALL_UIDAI_DEMOGRAPHICS if field not in matched
        )
        if disagreeing:
            return IssuerOutcome.PARTIAL_MATCH.value, disagreeing
        return IssuerOutcome.CONFIRMED.value, ()
