from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class IrrigationNocRead(BaseModel):
    noc_no: Optional[str] = Field(
        default=None,
        description=(
            "The NOC reference number as printed, spaces removed, as in "
            "'IRR/NOC/2026/0093'"
        ),
    )
    issued_by: Optional[str] = Field(
        default=None,
        description="The issuing office or department, as printed on the letterhead",
    )
    issue_date: Optional[str] = Field(
        default=None, description="The date the NOC was issued, as ISO yyyy-mm-dd"
    )
    valid_until: Optional[str] = Field(
        default=None,
        description=(
            "The date the NOC runs to, as ISO yyyy-mm-dd. Null if the letter states "
            "no validity period"
        ),
    )
    applicant: Optional[str] = Field(
        default=None, description="The applicant the NOC is accorded to, as printed"
    )
    survey_no: Optional[str] = Field(
        default=None,
        description=(
            "The survey number of the site the NOC covers, as printed, as in '77/2'"
        ),
    )
    buffer_condition: Optional[str] = Field(
        default=None,
        description=(
            "What the letter says about the FTL or buffer zone and any setback "
            "imposed, as one sentence"
        ),
    )
    seal_present: bool = Field(
        default=True, description="True if the department's seal is stamped on the letter"
    )
    signature_present: bool = Field(
        default=True,
        description="True if the letter is signed by the competent authority",
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


EXTRACT_IRRIGATION_NOC_PROMPT = """These images are the pages of ONE no-objection certificate
issued by a State Irrigation or Irrigation and CAD Department, clearing a site with reference to
a nearby water body — a tank, canal, stream or foreshore. It is a letter on department
letterhead, usually one or two pages, and it may be scanned, photographed, low-contrast or
rotated. The conditions are often on a second page or an annexure.

Read it into the response schema:
- noc_no: the NOC reference number as printed, with spaces removed. It reads as an office code,
  then 'NOC', then a year, then a serial — 'IRR/NOC/2026/0093', sometimes printed
  'Lr.No. IRR / NOC / 2026 / 0093'. Do NOT return the applicant's own file or application
  number if both appear; the NOC number is the one the department issued this letter under.
- issued_by: the issuing office as printed on the letterhead, e.g. 'Irrigation and CAD
  Department'. Give the department or circle, not the signatory's name.
- issue_date: the date the letter was issued, as ISO yyyy-mm-dd. It is printed near the
  reference number or beside the signature, usually dd-mm-yyyy.
- valid_until: the date the NOC runs to, as ISO yyyy-mm-dd. It is printed as 'valid until',
  'valid for a period of' or 'shall remain in force up to'. If the letter gives a period rather
  than a date ('valid for two years from the date of issue'), work the date out from
  issue_date. Leave it null if the letter states no validity period at all — that is different
  from a date you could not read.
- applicant: the person or firm the NOC is accorded to, exactly as printed.
- survey_no: the survey number of the site, as printed. Give it as it appears, including any
  sub-division ('77/2', '142/2A'). If the letter lists several, give the first.
- buffer_condition: what the letter says about the FTL (full tank level) or buffer zone and any
  setback it imposes, as one sentence in the letter's own words, e.g. 'Site lies outside the FTL
  buffer. No construction within 9 m of the tank bund.' This is the substance of the clearance,
  so keep the distance and the direction it applies to.
- seal_present, signature_present: whether each is actually visible. Report false only when you
  can see the page that should carry it and the element is genuinely absent.
- confidence: your overall confidence in this read, 0 to 1.
- low_confidence_fields: the labels of any fields you are unsure about, so a human can check
  them. Use the labels 'nocNo', 'issuedBy', 'issueDate', 'validUpto', 'applicant', 'surveyNo',
  'bufferCondition'.
- boxes: for each field you read, where you read it from. Use the same labels, and give the box
  as [ymin, xmin, ymax, xmax] normalised to 0-1000 on that page, with a 0-based page index.

Do not guess a value you cannot see. Leave a field null rather than inventing it, and say so in
low_confidence_fields when you are working from a partial or blurred read. In particular, do not
infer that a site is outside the buffer because the letter grants the NOC — report only what the
condition actually says."""

IRRIGATION_NOC_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.IRRIGATION_NOC.value,
    response_schema=IrrigationNocRead,
    prompt=EXTRACT_IRRIGATION_NOC_PROMPT,
    field_keys_by_attribute={
        "noc_no": "nocNo",
        "issued_by": "issuedBy",
        "issue_date": "issueDate",
        "valid_until": "validUpto",
        "applicant": "applicant",
        "survey_no": "surveyNo",
        "buffer_condition": "bufferCondition",
    },
    structure_keys_by_attribute={
        "seal_present": "seal",
        "signature_present": "signature",
    },
)
