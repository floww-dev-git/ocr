from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class OrcRead(BaseModel):
    orc_no: Optional[str] = Field(
        default=None,
        description="The ORC number or proceedings number, as printed, spaces removed",
    )
    issued_by: Optional[str] = Field(
        default=None,
        description="The issuing office, e.g. 'Revenue Divisional Officer, Chevella'",
    )
    issue_date: Optional[str] = Field(
        default=None, description="The date the certificate was issued, as ISO yyyy-mm-dd"
    )
    occupant: Optional[str] = Field(
        default=None,
        description="The occupant the rights are granted to, exactly as printed",
    )
    survey_no: Optional[str] = Field(
        default=None,
        description="The survey number of the Inam land, as printed, e.g. '77/2'",
    )
    village: Optional[str] = Field(
        default=None, description="The village the land lies in, as printed"
    )
    extent: Optional[str] = Field(
        default=None,
        description="The extent granted, as printed prose, e.g. '420 sq. yds'",
    )
    inam_category: Optional[str] = Field(
        default=None,
        description=(
            "The category of Inam land, as printed, e.g. 'Devadayam', "
            "'service Inam', 'religious Inam'"
        ),
    )
    seal_present: bool = Field(
        default=True, description="True if the office seal is on the certificate"
    )
    signature_present: bool = Field(
        default=True, description="True if the certificate is signed by the authority"
    )
    confidence: float = Field(
        default=0.0, description="Overall confidence in this read, 0..1"
    )
    low_confidence_fields: List[str] = Field(
        default_factory=list,
        description="Field labels you are unsure about, for human review",
    )
    boxes: List[FieldBoxRead] = Field(
        default_factory=list, description="Where each value was read from"
    )


EXTRACT_ORC_PROMPT = """These images are the pages of ONE Occupancy Rights Certificate (ORC)
issued by a Revenue Divisional Officer in respect of Inam land, granting occupancy rights to the
holder. It is an order on department letterhead, and it may be scanned, photographed,
low-contrast or rotated.

Read it into the response schema:
- orc_no: the ORC number or proceedings number, with spaces removed. Do NOT return the
  applicant's own file number if both appear.
- issued_by: the issuing office as printed, e.g. 'Revenue Divisional Officer, Chevella'.
- issue_date: the date the certificate was issued, as ISO yyyy-mm-dd.
- occupant: the person the occupancy rights are granted to, exactly as printed.
- survey_no: the survey number of the Inam land, as printed, including any sub-division.
- village: the village the land lies in, as printed.
- extent: the extent granted, as printed prose. Keep the leading number and its unit.
- inam_category: the category of Inam land, as printed ('Devadayam', 'service Inam',
  'religious Inam', 'personal Inam').
- seal_present, signature_present: whether each is actually visible. Report false only when you
  can see the page that should carry it and the element is genuinely absent.
- confidence: your overall confidence in this read, 0 to 1.
- low_confidence_fields: the labels of any fields you are unsure about, so a human can check
  them. Use the labels 'orcNo', 'issuedBy', 'issueDate', 'occupant', 'surveyNo', 'village',
  'extent', 'inamCategory'.
- boxes: for each field you read, where you read it from. Use the same labels, and give the box
  as [ymin, xmin, ymax, xmax] normalised to 0-1000 on that page, with a 0-based page index.

Do not guess a value you cannot see. Leave a field null rather than inventing it, and say so in
low_confidence_fields when you are working from a partial or blurred read."""

ORC_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.ORC.value,
    response_schema=OrcRead,
    prompt=EXTRACT_ORC_PROMPT,
    field_keys_by_attribute={
        "orc_no": "orcNo",
        "issued_by": "issuedBy",
        "issue_date": "issueDate",
        "occupant": "occupant",
        "survey_no": "surveyNo",
        "village": "village",
        "extent": "extent",
        "inam_category": "inamCategory",
    },
    structure_keys_by_attribute={
        "seal_present": "seal",
        "signature_present": "signature",
    },
)
