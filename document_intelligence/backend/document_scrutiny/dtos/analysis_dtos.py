from dataclasses import dataclass
from typing import Optional

from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.ownership_report_dtos import OwnershipReportDTO
from document_scrutiny.dtos.summary_dtos import ScrutinySummaryDTO


@dataclass(frozen=True)
class AnalyzeThreadRequestDTO:
    thread_id: str


@dataclass(frozen=True)
class AnalyzeDocumentRequestDTO:
    thread_id: str
    document_id: str


@dataclass(frozen=True)
class AnalysisEventDTO:
    event_type: str
    step: Optional[str] = None
    step_state: Optional[str] = None
    check_count: Optional[int] = None
    document: Optional[DocumentStateDTO] = None
    summary: Optional[ScrutinySummaryDTO] = None
    ownership_report: Optional[OwnershipReportDTO] = None
    message: Optional[str] = None
