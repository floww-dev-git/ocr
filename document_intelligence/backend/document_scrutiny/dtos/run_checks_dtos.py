from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from document_catalog.dtos.catalog_dtos import ApplicationDTO, DocumentTypeDTO
from document_extraction.dtos.document_record_dtos import DocumentQualityDTO
from document_scrutiny.dtos.document_dtos import FieldValueDTO


@dataclass(frozen=True)
class RunDocumentChecksRequestDTO:
    document_id: str
    document_type: DocumentTypeDTO
    application: ApplicationDTO
    # The date the scrutiny is being carried out on. Carried on the request rather
    # than read from the clock, so a re-run of the same evidence gives the same
    # answer and a seeded expiry date keeps meaning what it was written to mean.
    scrutiny_today: str
    field_values: Tuple[FieldValueDTO, ...] = ()
    structure_findings: Mapping[str, bool] = field(default_factory=dict)
    # What a QR on the document carries, for the integrity check. None when none.
    qr_fields: Optional[Mapping[str, str]] = None
    # How legible the scan was, for the quality check. None when not assessed.
    quality: Optional[DocumentQualityDTO] = None
