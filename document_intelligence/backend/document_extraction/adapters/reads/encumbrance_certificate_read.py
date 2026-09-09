from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class EncumbranceCertificateRead(BaseModel):
    ec_no: Optional[str] = Field(
        default=None,
        description="The EC number or application number as printed, spaces removed",
    )
    period: Optional[str] = Field(
        default=None,
        description=(
            "The period the search covers, as printed, e.g. '01-01-2000 to "
            "31-12-2024'"
        ),
    )
    survey_no: Optional[str] = Field(
        default=None,
        description="The survey number the certificate covers, as printed, e.g. '77/2'",
    )
    owner: Optional[str] = Field(
        default=None,
        description="The owner on record for the property, exactly as printed",
    )
    encumbrances: Optional[str] = Field(
        default=None,
        description=(
            "What the certificate reports found against the property. If it records "
            "no encumbrance, say so in the certificate's own words, e.g. 'Nil' or "
            "'No encumbrances for the period searched'"
        ),
    )
    seal_present: bool = Field(
        default=True, description="True if the sub-registrar's seal is on the certificate"
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


EXTRACT_ENCUMBRANCE_CERTIFICATE_PROMPT = """These images are the pages of ONE Encumbrance
Certificate (EC) issued by a State Registration Department sub-registrar office. It lists the
registered transactions found against a property over a stated period, and it may be scanned,
photographed, low-contrast or rotated. The transaction table often runs over several pages.

Read it into the response schema:
- ec_no: the EC number or the application number the certificate was issued under, with spaces
  removed. Do NOT return an individual document number from a row of the transaction table.
- period: the period the search covers, as printed. Keep both endpoints, e.g.
  '01-01-2000 to 31-12-2024'.
- survey_no: the survey number of the property, as printed, including any sub-division ('77/2').
- owner: the owner on record for the property, exactly as printed. If several owners appear over
  the period, give the current holder named in the certificate's conclusion.
- encumbrances: what the certificate found. If it records none, give the certificate's own
  wording ('Nil', 'No encumbrances for the period searched'). If it lists mortgages, liens or
  attachments, summarise them in one line. Do not read "nil" as an absence of the field.
- seal_present, signature_present: whether each is actually visible. Report false only when you
  can see the page that should carry it and the element is genuinely absent.
- confidence: your overall confidence in this read, 0 to 1.
- low_confidence_fields: the labels of any fields you are unsure about, so a human can check
  them. Use the labels 'ecNo', 'period', 'surveyNo', 'owner', 'encumbrances'.
- boxes: for each field you read, where you read it from. Use the same labels, and give the box
  as [ymin, xmin, ymax, xmax] normalised to 0-1000 on that page, with a 0-based page index.

Do not guess a value you cannot see. Leave a field null rather than inventing it, and say so in
low_confidence_fields when you are working from a partial or blurred read."""

ENCUMBRANCE_CERTIFICATE_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE.value,
    response_schema=EncumbranceCertificateRead,
    prompt=EXTRACT_ENCUMBRANCE_CERTIFICATE_PROMPT,
    field_keys_by_attribute={
        "ec_no": "ecNo",
        "period": "period",
        "survey_no": "surveyNo",
        "owner": "owner",
        "encumbrances": "encumbrances",
    },
    structure_keys_by_attribute={
        "seal_present": "seal",
        "signature_present": "signature",
    },
)
