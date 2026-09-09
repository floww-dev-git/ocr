import json
from typing import Any, Dict

from document_scrutiny.constants.analysis_constants import AnalysisEventType
from document_scrutiny.dtos.analysis_dtos import AnalysisEventDTO
from document_scrutiny.presenters.document_presenter import DocumentPresenter
from document_scrutiny.presenters.ownership_report_presenter import (
    OwnershipReportPresenter,
)

FRAME_TEMPLATE = "event: {event_type}\ndata: {payload}\n\n"


class ScrutinyStreamPresenter:
    @classmethod
    def format_frame(cls, event: AnalysisEventDTO) -> str:
        return FRAME_TEMPLATE.format(
            event_type=event.event_type,
            payload=json.dumps(cls._build_payload(event), separators=(",", ":")),
        )

    @classmethod
    def _build_payload(cls, event: AnalysisEventDTO) -> Dict[str, Any]:
        if event.event_type == AnalysisEventType.STEP.value:
            return cls._step_payload(event)
        if event.event_type == AnalysisEventType.DOCUMENT.value:
            return DocumentPresenter.get_document_response(document=event.document)
        if event.event_type == AnalysisEventType.SUMMARY.value:
            return DocumentPresenter.get_summary_response(summary=event.summary)
        if event.event_type == AnalysisEventType.CHAIN.value:
            return OwnershipReportPresenter.get_report_response(
                report=event.ownership_report
            )
        if event.event_type == AnalysisEventType.ERROR.value:
            return {"message": event.message}
        return {"ok": True}

    @staticmethod
    def _step_payload(event: AnalysisEventDTO) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"step": event.step, "state": event.step_state}
        if event.check_count is not None:
            payload["count"] = event.check_count
        return payload
