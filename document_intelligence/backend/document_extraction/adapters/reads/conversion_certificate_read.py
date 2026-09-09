from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class ConversionCertificateRead(BaseModel):
    conversion_order_no: Optional[str] = Field(
        default=None,
        description="The conversion order or proceedings number, as printed, spaces removed",
    )
    issued_by: Optional[str] = Field(
        default=None,
        description="The issuing office, e.g. 'Revenue Divisional Officer, Rajendranagar'",
    )
    issue_date: Optional[str] = Field(
        default=None, description="The date the order was issued, as ISO yyyy-mm-dd"
    )
    applicant: Optional[str] = Field(
        default=None,
        description="The applicant the land was converted for, exactly as printed",
    )
    survey_no: Optional[str] = Field(
        default=None,
        description="The survey number of the converted land, as printed, e.g. '77/2'",
    )
    village: Optional[str] = Field(
        default=None, description="The village the land lies in, as printed"
    )
    extent: Optional[str] = Field(
        default=None,
        description=(
            "The extent converted, as printed prose, e.g. '420 sq. yds' or "
            "'0.35 acres'"
        ),
    )
    converted_use: Optional[str] = Field(
        default=None,
        description=(
            "The use the land was converted to, as printed, e.g. 'residential', "
            "'commercial'"
        ),
    )
    nala_assessment: Optional[str] = Field(
        default=None,
        description=(
            "The NALA conversion tax or assessment paid, as printed, e.g. "
            "'Rs. 1,05,000'"
        ),
    )
    seal_present: bool = Field(
        default=True, description="True if the office seal is on the order"
    )
    signature_present: bool = Field(
        default=True, description="True if the order is signed by the authority"
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


EXTRACT_CONVERSION_CERTIFICATE_PROMPT = """These images are the pages of ONE land conversion
certificate issued by a Revenue Divisional Officer under the Telangana Agricultural Land
(Conversion for Non-Agricultural Purposes) Act, 2006 (the NALA Act). It is an order converting
agricultural land to a non-agricultural use, on department letterhead, and it may be scanned,
photographed, low-contrast or rotated.

Read it into the response schema:
- conversion_order_no: the order or proceedings number the conversion was granted under, with
  spaces removed. Do NOT return the applicant's own file number if both appear.
- issued_by: the issuing office as printed, e.g. 'Revenue Divisional Officer, Rajendranagar'.
- issue_date: the date the order was issued, as ISO yyyy-mm-dd. It is usually printed dd-mm-yyyy.
- applicant: the person or firm the land was converted for, exactly as printed.
- survey_no: the survey number of the converted land, as printed, including any sub-division.
- village: the village the land lies in, as printed.
- extent: the extent converted, as printed prose. Keep the leading number and its unit
  ('420 sq. yds', '0.35 acres'); do not convert between units.
- converted_use: the use the land was converted to, as printed ('residential', 'commercial',
  'industrial').
- nala_assessment: the conversion tax or NALA assessment paid, as printed.
- seal_present, signature_present: whether each is actually visible. Report false only when you
  can see the page that should carry it and the element is genuinely absent.
- confidence: your overall confidence in this read, 0 to 1.
- low_confidence_fields: the labels of any fields you are unsure about, so a human can check
  them. Use the labels 'conversionOrderNo', 'issuedBy', 'issueDate', 'applicant', 'surveyNo',
  'village', 'extent', 'convertedUse', 'nalaAssessment'.
- boxes: for each field you read, where you read it from. Use the same labels, and give the box
  as [ymin, xmin, ymax, xmax] normalised to 0-1000 on that page, with a 0-based page index.

Do not guess a value you cannot see. Leave a field null rather than inventing it, and say so in
low_confidence_fields when you are working from a partial or blurred read."""

CONVERSION_CERTIFICATE_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.CONVERSION_CERT.value,
    response_schema=ConversionCertificateRead,
    prompt=EXTRACT_CONVERSION_CERTIFICATE_PROMPT,
    field_keys_by_attribute={
        "conversion_order_no": "conversionOrderNo",
        "issued_by": "issuedBy",
        "issue_date": "issueDate",
        "applicant": "applicant",
        "survey_no": "surveyNo",
        "village": "village",
        "extent": "extent",
        "converted_use": "convertedUse",
        "nala_assessment": "nalaAssessment",
    },
    structure_keys_by_attribute={
        "seal_present": "seal",
        "signature_present": "signature",
    },
)
