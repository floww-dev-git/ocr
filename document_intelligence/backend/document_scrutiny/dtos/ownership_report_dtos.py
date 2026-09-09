from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from document_scrutiny.dtos.chain_dtos import ChainOfTitleDTO


@dataclass(frozen=True)
class RiskSignalDTO:
    severity: str
    code: str
    title: str
    detail: str


@dataclass(frozen=True)
class RiskAssessmentDTO:
    """A risk picture for the chain, and every point it assigns.

    Display only. Nothing here changes a check, a document status or the thread
    verdict: an officer decides, and a score they cannot argue with is not evidence.
    """

    score: int
    level: str
    signals: Tuple[RiskSignalDTO, ...] = ()


@dataclass(frozen=True)
class PartySummaryDTO:
    name: str
    name_original: Optional[str] = None
    relative: Optional[str] = None
    # How many more people stood on this side of the deed beyond the one named.
    others_count: int = 0


@dataclass(frozen=True)
class PropertySummaryDTO:
    survey_no: Optional[str] = None
    plot_no: Optional[str] = None
    extent_text: Optional[str] = None
    locality: Optional[str] = None
    boundaries: Optional[str] = None


@dataclass(frozen=True)
class JourneyEntryDTO:
    """One row of the ownership journey, newest first.

    Owners and the transfers between them share one ordered list because that is the
    thing being described: a sequence, read top to bottom.
    """

    kind: str
    # An owner row.
    role: Optional[str] = None
    badge: Optional[str] = None
    party: Optional[PartySummaryDTO] = None
    meta: Optional[str] = None
    is_current: bool = False
    # A transfer row.
    verdict: Optional[str] = None
    label: Optional[str] = None
    reference: Optional[str] = None
    note: Optional[str] = None
    identity_score: Optional[int] = None


@dataclass(frozen=True)
class AttentionItemDTO:
    severity: str
    verb: str
    title: str
    detail: str
    action: str


@dataclass(frozen=True)
class DocumentRoleRowDTO:
    document_id: str
    deed_type: Optional[str]
    doc_no: Optional[str]
    date: Optional[str]
    is_root: bool = False


@dataclass(frozen=True)
class AuthorityDocumentDTO:
    document_id: str
    deed_type: Optional[str]
    doc_no: Optional[str]
    owner: str
    holder: str


@dataclass(frozen=True)
class ReportVerdictDTO:
    level: str
    headline: str
    plain: str


@dataclass(frozen=True)
class ReportStatsDTO:
    title_deed_count: int = 0
    span_from: Optional[str] = None
    span_to: Optional[str] = None
    need_review: int = 0
    breaks: int = 0


@dataclass(frozen=True)
class OwnershipReportDTO:
    thread_id: str
    verdict: ReportVerdictDTO
    stats: ReportStatsDTO
    property_summary: PropertySummaryDTO = field(default_factory=PropertySummaryDTO)
    journey: Tuple[JourneyEntryDTO, ...] = ()
    authority: Tuple[AuthorityDocumentDTO, ...] = ()
    documents_by_role: Mapping[str, Tuple[DocumentRoleRowDTO, ...]] = field(
        default_factory=dict
    )
    attention: Tuple[AttentionItemDTO, ...] = ()
    risk: Optional[RiskAssessmentDTO] = None
    chain: ChainOfTitleDTO = field(default_factory=ChainOfTitleDTO)

    @property
    def deed_count(self) -> int:
        """Every registered document considered, whatever role it turned out to play."""
        return sum(len(rows) for rows in self.documents_by_role.values())


@dataclass(frozen=True)
class OwnershipReportRequestDTO:
    thread_id: str
