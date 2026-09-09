import dataclasses
from typing import Dict, List, Sequence, Tuple

from document_scrutiny.constants.enums import CheckGroup
from document_scrutiny.dtos.check_dtos import CheckDTO


class CheckReconciliation:
    @classmethod
    def merge(
        cls,
        previous_checks: Sequence[CheckDTO],
        recomputed_checks: Sequence[CheckDTO],
    ) -> Tuple[Tuple[CheckDTO, ...], Tuple[str, ...]]:
        previous_by_id = {check.check_id: check for check in previous_checks}
        merged: List[CheckDTO] = [
            cls._carry_resolution(recomputed=recomputed, previous_by_id=previous_by_id)
            for recomputed in recomputed_checks
        ]
        merged.extend(cls._issuer_checks(previous_checks))
        return tuple(merged), cls._changed_ids(
            previous_by_id=previous_by_id, merged=merged
        )

    @staticmethod
    def _carry_resolution(
        recomputed: CheckDTO, previous_by_id: Dict[str, CheckDTO]
    ) -> CheckDTO:
        previous = previous_by_id.get(recomputed.check_id)
        if previous is None:
            return recomputed
        return dataclasses.replace(
            recomputed,
            acknowledged=previous.acknowledged,
            manual=previous.manual,
            requested=previous.requested,
        )

    @staticmethod
    def _issuer_checks(previous_checks: Sequence[CheckDTO]) -> List[CheckDTO]:
        # The issuer's answer is not derivable from what the officer typed, so it
        # survives a re-check untouched.
        return [
            check
            for check in previous_checks
            if check.group == CheckGroup.EXTERNAL.value
        ]

    @staticmethod
    def _changed_ids(
        previous_by_id: Dict[str, CheckDTO], merged: Sequence[CheckDTO]
    ) -> Tuple[str, ...]:
        changed = []
        for check in merged:
            previous = previous_by_id.get(check.check_id)
            if previous is None or previous.status != check.status:
                changed.append(check.check_id)
        # A check that stopped existing has changed as surely as one that moved,
        # and the client needs telling or it leaves a stale card on screen.
        merged_ids = {check.check_id for check in merged}
        changed.extend(
            check_id for check_id in previous_by_id if check_id not in merged_ids
        )
        return tuple(changed)
