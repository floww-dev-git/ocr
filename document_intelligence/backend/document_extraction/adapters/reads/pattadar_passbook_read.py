from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class PattadarPassbookRead(BaseModel):
    passbook_no: Optional[str] = Field(
        default=None,
        description="The pass book number as printed, spaces removed",
    )
    pattadar: Optional[str] = Field(
        default=None,
        description="The pattadar (title holder) name, exactly as printed",
    )
    khata_no: Optional[str] = Field(
        default=None, description="The khata or account number, as printed"
    )
    survey_no: Optional[str] = Field(
        default=None,
        description="The survey number the holding covers, as printed, e.g. '77/2'",
    )
    village: Optional[str] = Field(
        default=None, description="The village the holding lies in, as printed"
    )
    extent: Optional[str] = Field(
        default=None,
        description=(
            "The extent of the holding, as printed prose, e.g. '420 sq. yds' or "
            "'0.35 acres'. If several survey entries are listed, give the total"
        ),
    )
    land_classification: Optional[str] = Field(
        default=None,
        description=(
            "The land classification as printed, e.g. 'Patta', 'Dry', 'Wet', "
            "'Assessed waste'"
        ),
    )
    issue_date: Optional[str] = Field(
        default=None, description="The date the pass book was issued, as ISO yyyy-mm-dd"
    )
    photograph_present: bool = Field(
        default=True, description="True if the pattadar's photograph is printed"
    )
    seal_present: bool = Field(
        default=True, description="True if the revenue seal is on the pass book"
    )
    signature_present: bool = Field(
        default=True, description="True if the Tahsildar's signature is present"
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


EXTRACT_PATTADAR_PASSBOOK_PROMPT = """These images are the pages of ONE Pattadar Pass Book /
Title Deed issued by the Revenue Department (through the Dharani system) to the holder of
agricultural land. It is a booklet or card recording the holding, and it may be scanned,
photographed, low-contrast or rotated.

Read it into the response schema:
- passbook_no: the pass book number, with spaces removed.
- pattadar: the pattadar (title holder) name, exactly as printed, preserving its capitalisation.
- khata_no: the khata or account number, as printed.
- survey_no: the survey number of the holding, as printed, including any sub-division. If the
  book lists several survey numbers, give the first.
- village: the village the holding lies in, as printed.
- extent: the extent of the holding, as printed prose. Keep the leading number and its unit. If
  several entries are listed, give the total the book states, not one row.
- land_classification: the classification as printed ('Patta', 'Dry', 'Wet', 'Assessed waste').
- issue_date: the date the pass book was issued, as ISO yyyy-mm-dd.
- photograph_present, seal_present, signature_present: whether each is actually visible. Report
  false only when you can see the page that should carry it and the element is genuinely absent.
- confidence: your overall confidence in this read, 0 to 1.
- low_confidence_fields: the labels of any fields you are unsure about, so a human can check
  them. Use the labels 'passbookNo', 'pattadar', 'khataNo', 'surveyNo', 'village', 'extent',
  'landClassification', 'issueDate'.
- boxes: for each field you read, where you read it from. Use the same labels, and give the box
  as [ymin, xmin, ymax, xmax] normalised to 0-1000 on that page, with a 0-based page index.

Do not guess a value you cannot see. Leave a field null rather than inventing it, and say so in
low_confidence_fields when you are working from a partial or blurred read."""

PATTADAR_PASSBOOK_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.PATTADAR_PASSBOOK.value,
    response_schema=PattadarPassbookRead,
    prompt=EXTRACT_PATTADAR_PASSBOOK_PROMPT,
    field_keys_by_attribute={
        "passbook_no": "passbookNo",
        "pattadar": "pattadar",
        "khata_no": "khataNo",
        "survey_no": "surveyNo",
        "village": "village",
        "extent": "extent",
        "land_classification": "landClassification",
        "issue_date": "issueDate",
    },
    structure_keys_by_attribute={
        "photograph_present": "photo",
        "seal_present": "seal",
        "signature_present": "signature",
    },
)
