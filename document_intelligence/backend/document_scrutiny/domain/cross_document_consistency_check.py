from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from document_scrutiny.constants.check_thresholds import NAME_MATCH_WARNING_FLOOR
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.name_similarity import NameSimilarity
from document_scrutiny.dtos.check_dtos import CheckDTO

CROSS_DOCUMENT_CHECK_KEY = "cross-document"

AGREES_TITLE = "Name agrees across the documents"
AGREES_DETAIL = "The name on this document matches the other documents on the file."
DISAGREES_TITLE = "Name does not match another document"


@dataclass(frozen=True)
class SiblingName:
    """A name read off another document on the same file, with that document's label."""

    document_type_label: str
    name: str


class CrossDocumentConsistencyCheck:
    """Whether identity documents on one file name the same person as each other.

    This is the only check that looks across documents rather than at one document
    against the application: an Aadhaar and a PAN filed together should carry the
    same name, and a disagreement between them is worth surfacing even when each
    happens to sit close to the application form. It reuses the same name-similarity
    the field checks use, and reports at the same WARN grain — a near-match is a
    look, not a failure.

    Returns None when there is no sibling name to compare against, so the first
    identity document on a file is simply not cross-checked until a second arrives.
    """

    @classmethod
    def build(
        cls,
        document_id: str,
        name: Optional[str],
        siblings: Sequence[SiblingName],
    ) -> Optional[CheckDTO]:
        own_name = str(name or "").strip()
        if not own_name or not siblings:
            return None
        disagreements = cls._disagreements(own_name=own_name, siblings=siblings)
        if not disagreements:
            return cls._check(
                document_id=document_id,
                status=CheckStatus.PASS.value,
                title=AGREES_TITLE,
                detail=AGREES_DETAIL,
            )
        return cls._check(
            document_id=document_id,
            status=CheckStatus.WARN.value,
            title=DISAGREES_TITLE,
            detail=cls._disagreement_detail(own_name=own_name, disagreements=disagreements),
        )

    @classmethod
    def _disagreements(
        cls, own_name: str, siblings: Sequence[SiblingName]
    ) -> List[SiblingName]:
        disagreeing = []
        for sibling in siblings:
            if not str(sibling.name or "").strip():
                continue
            similarity = NameSimilarity.calculate(
                name=own_name, comparison_name=sibling.name
            )
            if similarity < NAME_MATCH_WARNING_FLOOR:
                disagreeing.append(sibling)
        return disagreeing

    @staticmethod
    def _disagreement_detail(own_name: str, disagreements: List[SiblingName]) -> str:
        others = "; ".join(
            f"the {sibling.document_type_label} reads {sibling.name}"
            for sibling in disagreements
        )
        return (
            f"This document reads {own_name}, but {others}. The documents on this "
            "file should name the same person, so check them against the originals."
        )

    @staticmethod
    def _check(
        document_id: str, status: str, title: str, detail: str
    ) -> CheckDTO:
        return CheckDTO(
            check_id=f"{document_id}:{CROSS_DOCUMENT_CHECK_KEY}",
            document_id=document_id,
            group=CheckGroup.CROSS.value,
            title=title,
            status=status,
            detail=detail,
        )
