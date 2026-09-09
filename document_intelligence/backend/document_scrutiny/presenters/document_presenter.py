from typing import Any, Dict, List, Optional

from document_extraction.dtos.deed_record_dtos import (
    DeedRecordDTO,
    PartyDTO,
    PropertyInfoDTO,
)
from document_scrutiny.dtos.check_dtos import CheckDTO, IssuerCallDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO, FieldValueDTO
from document_scrutiny.dtos.note_dtos import ScrutinyNoteDTO
from document_scrutiny.dtos.officer_action_dtos import CheckChangeDTO, DocumentChangeDTO
from document_scrutiny.dtos.summary_dtos import OpenItemDTO, ScrutinySummaryDTO
from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO


class DocumentPresenter:
    @classmethod
    def get_thread_response(cls, thread: ScrutinyThreadDTO) -> Dict[str, Any]:
        return {
            "threadId": thread.thread_id,
            "applicationId": thread.application_id,
            "serviceOverrides": dict(thread.service_overrides),
            "documents": [
                cls.get_document_response(document=document)
                for document in thread.documents
            ],
        }

    @classmethod
    def get_document_response(cls, document: DocumentStateDTO) -> Dict[str, Any]:
        return {
            "documentId": document.document_id,
            "filename": document.filename,
            "fileFormat": document.file_format,
            "fileSizeBytes": document.file_size_bytes,
            "documentTypeId": document.document_type_id,
            "documentTypeLabel": document.document_type_label,
            "typeConfidence": document.type_confidence,
            "implemented": document.implemented,
            "stage": document.stage,
            "status": document.status,
            "confirmed": document.confirmed,
            "pageCount": document.page_count,
            "fieldValues": [
                cls._prep_field_value_response(field_value)
                for field_value in document.field_values
            ],
            "structureFindings": dict(document.structure_findings),
            "checks": [cls.get_check_response(check=check) for check in document.checks],
            "pageImageUrls": list(document.page_image_urls),
            "deedRecord": cls._prep_deed_record_response(document.deed_record),
            "parentDocumentId": document.parent_document_id,
            "pageStart": document.page_start,
            "pageEnd": document.page_end,
        }

    @classmethod
    def _prep_deed_record_response(
        cls, deed_record: Optional[DeedRecordDTO]
    ) -> Optional[Dict[str, Any]]:
        if deed_record is None:
            return None
        return {
            "docNo": deed_record.doc_no,
            "sro": deed_record.sro,
            "registrationDate": deed_record.registration_date,
            "executionDate": deed_record.execution_date,
            "deedType": deed_record.deed_type,
            "sellers": [cls._prep_party_response(party) for party in deed_record.sellers],
            "buyers": [cls._prep_party_response(party) for party in deed_record.buyers],
            "property": cls._prep_property_response(deed_record.property_info),
            "considerationText": deed_record.consideration_text,
            "considerationInr": deed_record.consideration_inr,
            "stampDutyText": deed_record.stamp_duty_text,
            "estampNo": deed_record.estamp_no,
            "priorDeedRefs": list(deed_record.prior_deed_refs),
            "executedViaGpa": deed_record.executed_via_gpa,
        }

    @staticmethod
    def _prep_party_response(party: PartyDTO) -> Dict[str, Any]:
        return {
            "name": party.name,
            "nameOriginal": party.name_original,
            "relation": party.relation,
            "relativeName": party.relative_name,
            "address": party.address,
            "pan": party.pan,
            "aadhaar": party.aadhaar,
        }

    @staticmethod
    def _prep_property_response(property_info: PropertyInfoDTO) -> Dict[str, Any]:
        return {
            "surveyNo": property_info.survey_no,
            "plotNo": property_info.plot_no,
            "extentText": property_info.extent_text,
            "extentSqYard": property_info.extent_sq_yard,
            "boundaries": property_info.boundaries,
            "locality": property_info.locality,
            "ulpin": property_info.ulpin,
        }

    @classmethod
    def get_check_response(cls, check: CheckDTO) -> Dict[str, Any]:
        return {
            "checkId": check.check_id,
            "documentId": check.document_id,
            "group": check.group,
            "title": check.title,
            "status": check.status,
            "detail": check.detail,
            "fieldKey": check.field_key,
            "acknowledged": check.acknowledged,
            "manual": check.manual,
            "requested": check.requested,
            "issuerCall": cls._prep_issuer_call_response(check.issuer_call),
        }

    @classmethod
    def get_summary_response(cls, summary: ScrutinySummaryDTO) -> Dict[str, Any]:
        return {
            "threadStatus": summary.thread_status,
            "documentCount": summary.document_count,
            "confirmedDocumentCount": summary.confirmed_document_count,
            "statusCounts": dict(summary.status_counts),
            "openItems": [
                cls._prep_open_item_response(open_item)
                for open_item in summary.open_items
            ],
        }

    @classmethod
    def get_documents_response(
        cls, documents: List[DocumentStateDTO]
    ) -> Dict[str, Any]:
        return {
            "documents": [
                cls.get_document_response(document=document) for document in documents
            ]
        }

    @classmethod
    def get_document_change_response(cls, change: DocumentChangeDTO) -> Dict[str, Any]:
        return {
            "document": cls.get_document_response(document=change.document),
            "summary": cls.get_summary_response(summary=change.summary),
            "changedCheckIds": list(change.changed_check_ids),
        }

    @classmethod
    def get_check_change_response(cls, change: CheckChangeDTO) -> Dict[str, Any]:
        return {
            "check": cls.get_check_response(check=change.check),
            "document": cls.get_document_response(document=change.document),
            "summary": cls.get_summary_response(summary=change.summary),
        }

    @staticmethod
    def get_note_response(note: ScrutinyNoteDTO) -> Dict[str, Any]:
        return {"threadId": note.thread_id, "text": note.text}

    @staticmethod
    def _prep_field_value_response(field_value: FieldValueDTO) -> Dict[str, Any]:
        return {
            "key": field_value.key,
            "value": field_value.value,
            "confidence": field_value.confidence,
            "edited": field_value.edited,
            "confirmed": field_value.confirmed,
        }

    @staticmethod
    def _prep_issuer_call_response(
        issuer_call: Optional[IssuerCallDTO],
    ) -> Optional[Dict[str, Any]]:
        if issuer_call is None:
            return None
        return {
            "issuerServiceId": issuer_call.issuer_service_id,
            "name": issuer_call.name,
            "endpoint": issuer_call.endpoint,
            "latencyMs": issuer_call.latency_ms,
            "requestPayload": dict(issuer_call.request_payload),
            "responsePayload": (
                dict(issuer_call.response_payload)
                if issuer_call.response_payload is not None
                else None
            ),
        }

    @staticmethod
    def _prep_open_item_response(open_item: OpenItemDTO) -> Dict[str, Any]:
        return {
            "documentId": open_item.document_id,
            "checkId": open_item.check_id,
            "text": open_item.text,
        }
