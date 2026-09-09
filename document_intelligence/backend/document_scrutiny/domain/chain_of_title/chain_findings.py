from typing import Sequence, Tuple

from document_scrutiny.constants.chain_constants import (
    CLEAN_LINK_DETAIL,
    FINDING_TITLES,
    SEVERITY_BY_LINK_VERDICT,
    SEVERITY_ORDER,
    FindingSeverity,
)
from document_scrutiny.dtos.chain_dtos import ChainFindingDTO, ChainLinkDTO

UNRANKED_SEVERITY_POSITION = len(SEVERITY_ORDER) + 1


class ChainFindings:
    """Turns per-link verdicts into what the officer should read, worst first.

    A clean link still produces a finding. The officer needs to see that a link was
    examined and held, not infer it from an absence.
    """

    @classmethod
    def build(cls, links: Sequence[ChainLinkDTO]) -> Tuple[ChainFindingDTO, ...]:
        findings = [cls._build_one(link=link) for link in links]
        findings.sort(key=lambda finding: cls._position(finding.severity))
        return tuple(findings)

    @classmethod
    def _build_one(cls, link: ChainLinkDTO) -> ChainFindingDTO:
        return ChainFindingDTO(
            severity=SEVERITY_BY_LINK_VERDICT.get(
                link.verdict, FindingSeverity.MEDIUM.value
            ),
            verdict=link.verdict,
            title=f"{FINDING_TITLES.get(link.verdict, link.verdict)} "
            f"({cls._describe(link.from_doc_no)} → {cls._describe(link.to_doc_no)})",
            detail=" ".join(link.notes) or CLEAN_LINK_DETAIL,
        )

    @staticmethod
    def _describe(doc_no) -> str:
        return str(doc_no or "unnumbered deed")

    @staticmethod
    def _position(severity: str) -> int:
        if severity in SEVERITY_ORDER:
            return SEVERITY_ORDER.index(severity)
        return UNRANKED_SEVERITY_POSITION
