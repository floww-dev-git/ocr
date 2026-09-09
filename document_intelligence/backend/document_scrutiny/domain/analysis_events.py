from typing import Optional

from document_scrutiny.constants.analysis_constants import (
    AnalysisEventType,
    AnalysisStep,
    StepState,
)
from document_scrutiny.dtos.analysis_dtos import AnalysisEventDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.ownership_report_dtos import OwnershipReportDTO
from document_scrutiny.dtos.summary_dtos import ScrutinySummaryDTO


class AnalysisEvents:
    @staticmethod
    def step_running(step: AnalysisStep) -> AnalysisEventDTO:
        return AnalysisEventDTO(
            event_type=AnalysisEventType.STEP.value,
            step=step.value,
            step_state=StepState.RUNNING.value,
        )

    @staticmethod
    def step_done(step: AnalysisStep, check_count: Optional[int] = None) -> AnalysisEventDTO:
        return AnalysisEventDTO(
            event_type=AnalysisEventType.STEP.value,
            step=step.value,
            step_state=StepState.DONE.value,
            check_count=check_count,
        )

    @staticmethod
    def document(document: DocumentStateDTO) -> AnalysisEventDTO:
        return AnalysisEventDTO(
            event_type=AnalysisEventType.DOCUMENT.value, document=document
        )

    @staticmethod
    def summary(summary: ScrutinySummaryDTO) -> AnalysisEventDTO:
        return AnalysisEventDTO(
            event_type=AnalysisEventType.SUMMARY.value, summary=summary
        )

    @staticmethod
    def chain(ownership_report: OwnershipReportDTO) -> AnalysisEventDTO:
        return AnalysisEventDTO(
            event_type=AnalysisEventType.CHAIN.value,
            ownership_report=ownership_report,
        )

    @staticmethod
    def error(message: str) -> AnalysisEventDTO:
        return AnalysisEventDTO(
            event_type=AnalysisEventType.ERROR.value, message=message
        )

    @staticmethod
    def done() -> AnalysisEventDTO:
        return AnalysisEventDTO(event_type=AnalysisEventType.DONE.value)
