import dataclasses
from typing import Optional, Tuple

from document_extraction.dtos.extraction_dtos import DocumentClassificationDTO
from document_extraction.dtos.document_record_dtos import DocumentRecordDTO
from document_scrutiny.constants.enums import DocumentStage
from document_scrutiny.domain.document_verdict import DocumentVerdict
from document_scrutiny.dtos.check_dtos import CheckDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO, FieldValueDTO


class DocumentProgress:
    @classmethod
    def with_classification(
        cls,
        document: DocumentStateDTO,
        classification: DocumentClassificationDTO,
    ) -> DocumentStateDTO:
        return cls._with_status(
            dataclasses.replace(
                document,
                document_type_id=classification.document_type_id,
                document_type_label=classification.document_type_label,
                type_confidence=classification.type_confidence,
                implemented=classification.implemented,
                page_count=classification.page_count,
                stage=DocumentStage.IDENTIFYING.value,
            )
        )

    @classmethod
    def with_read(
        cls, document: DocumentStateDTO, record: DocumentRecordDTO
    ) -> DocumentStateDTO:
        return cls._with_status(
            dataclasses.replace(
                document,
                field_values=cls._prep_field_values(record),
                structure_findings=dict(record.structure_findings),
                page_count=record.page_count,
                stage=DocumentStage.EXTRACTING.value,
                deed_record=record.deed_record,
                qr_fields=record.qr_fields,
                quality=record.quality,
            )
        )

    @classmethod
    def with_stage(
        cls,
        document: DocumentStateDTO,
        stage: str,
        checks: Optional[Tuple[CheckDTO, ...]] = None,
    ) -> DocumentStateDTO:
        return cls._with_status(
            dataclasses.replace(
                document,
                stage=stage,
                checks=document.checks if checks is None else checks,
            )
        )

    @staticmethod
    def _with_status(document: DocumentStateDTO) -> DocumentStateDTO:
        return dataclasses.replace(
            document,
            status=DocumentVerdict.derive(stage=document.stage, checks=document.checks),
        )

    @staticmethod
    def _prep_field_values(record: DocumentRecordDTO) -> Tuple[FieldValueDTO, ...]:
        return tuple(
            FieldValueDTO(
                key=field_read.key,
                value=field_read.value,
                confidence=field_read.confidence,
            )
            for field_read in record.field_reads
        )
