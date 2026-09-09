from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class MarketValueCertificateRead(BaseModel):
    certificate_no: Optional[str] = Field(
        default=None,
        description="The certificate number as printed, spaces removed",
    )
    sro: Optional[str] = Field(
        default=None,
        description="The sub-registrar office that issued it, as printed",
    )
    issue_date: Optional[str] = Field(
        default=None, description="The date the certificate was issued, as ISO yyyy-mm-dd"
    )
    survey_no: Optional[str] = Field(
        default=None,
        description="The survey number the valuation is for, as printed, e.g. '77/2'",
    )
    village: Optional[str] = Field(
        default=None, description="The village the land lies in, as printed"
    )
    market_value_per_sq_yd: Optional[str] = Field(
        default=None,
        description=(
            "The market value per square yard, as printed prose, e.g. "
            "'Rs. 45,000 per sq. yd'"
        ),
    )
    valuation_as_on: Optional[str] = Field(
        default=None,
        description="The date the valuation is effective as on, as ISO yyyy-mm-dd",
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


EXTRACT_MARKET_VALUE_CERTIFICATE_PROMPT = """These images are the pages of ONE market value
certificate issued by the concerned sub-registrar office, stating the government market value of
a plot per square yard as on a date. It is a short letter or a stamped statement, and it may be
scanned, photographed, low-contrast or rotated.

Read it into the response schema:
- certificate_no: the certificate number, with spaces removed.
- sro: the sub-registrar office that issued it, as printed.
- issue_date: the date the certificate was issued, as ISO yyyy-mm-dd.
- survey_no: the survey number the valuation is for, as printed, including any sub-division.
- village: the village the land lies in, as printed.
- market_value_per_sq_yd: the market value per square yard, as printed prose. Keep the amount
  and its unit ('Rs. 45,000 per sq. yd'). If the certificate gives a value per acre or per sq.
  metre instead, give it verbatim as printed rather than converting.
- valuation_as_on: the date the value is effective as on, as ISO yyyy-mm-dd. This is often the
  same as the issue date but not always; give it only if the certificate states it separately.
- seal_present, signature_present: whether each is actually visible. Report false only when you
  can see the page that should carry it and the element is genuinely absent.
- confidence: your overall confidence in this read, 0 to 1.
- low_confidence_fields: the labels of any fields you are unsure about, so a human can check
  them. Use the labels 'certificateNo', 'sro', 'issueDate', 'surveyNo', 'village',
  'marketValuePerSqYd', 'valuationAsOn'.
- boxes: for each field you read, where you read it from. Use the same labels, and give the box
  as [ymin, xmin, ymax, xmax] normalised to 0-1000 on that page, with a 0-based page index.

Do not guess a value you cannot see. Leave a field null rather than inventing it, and say so in
low_confidence_fields when you are working from a partial or blurred read."""

MARKET_VALUE_CERTIFICATE_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.MARKET_VALUE_CERT.value,
    response_schema=MarketValueCertificateRead,
    prompt=EXTRACT_MARKET_VALUE_CERTIFICATE_PROMPT,
    field_keys_by_attribute={
        "certificate_no": "certificateNo",
        "sro": "sro",
        "issue_date": "issueDate",
        "survey_no": "surveyNo",
        "village": "village",
        "market_value_per_sq_yd": "marketValuePerSqYd",
        "valuation_as_on": "valuationAsOn",
    },
    structure_keys_by_attribute={
        "seal_present": "seal",
        "signature_present": "signature",
    },
)
