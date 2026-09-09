from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class PanCardRead(BaseModel):
    name: Optional[str] = Field(
        default=None, description="Cardholder name exactly as printed"
    )
    parent_name: Optional[str] = Field(
        default=None, description="Father's name exactly as printed"
    )
    date_of_birth: Optional[str] = Field(
        default=None, description="Date of birth as ISO yyyy-mm-dd"
    )
    pan: Optional[str] = Field(
        default=None, description="The ten-character permanent account number"
    )
    photograph_present: Optional[bool] = Field(
        default=True, description="True if a photograph is printed on the card"
    )
    signature_present: Optional[bool] = Field(
        default=True,
        description=(
            "True if the card is signed. A handwritten signature counts, and so "
            "does an e-PAN's 'Digitally signed by DS INCOME TAX DEPT' block"
        ),
    )
    hologram_present: Optional[bool] = Field(
        default=True,
        description=(
            "True if a hologram is visible. Null if this is an e-PAN, which is "
            "issued without one, so the question does not apply"
        ),
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


EXTRACT_PAN_PROMPT = """These images are the pages of ONE Indian PAN card (Permanent Account
Number card issued by the Income Tax Department). The pages may be scanned, photographed,
low-contrast, or rotated.

Read it into the response schema:
- name: the cardholder's name exactly as printed, preserving its capitalisation.
- parent_name: the father's name exactly as printed.
- date_of_birth: normalise to ISO yyyy-mm-dd. A PAN card usually prints dd/mm/yyyy.
- pan: the ten-character account number, five letters then four digits then one letter.
- photograph_present, signature_present, hologram_present: whether each is actually visible on
  the card. Report false only when you can see the card and the element is genuinely absent.
  A PAN arrives in two forms and they carry different security features:
    * a physical laminated card, which has a handwritten signature and a hologram;
    * an e-PAN, printed or as a PDF, which instead carries a QR code and a
      'Digitally signed by DS INCOME TAX DEPT' block, and is issued with NO hologram.
  For an e-PAN, report signature_present true (it is signed, digitally) and leave
  hologram_present null — null means the element does not apply to this form of the
  document, which is different from a hologram that should be there and is missing.
- confidence: your overall confidence in this read, 0 to 1.
- low_confidence_fields: the labels of any fields you are unsure about, so a human can check
  them. Use the labels 'name', 'parentName', 'dob', 'pan'.
- boxes: for each field you read, where you read it from. Use the same labels, and give the box
  as [ymin, xmin, ymax, xmax] normalised to 0-1000 on that page, with a 0-based page index.

Do not guess a value you cannot see. Leave a field null rather than inventing it, and say so in
low_confidence_fields when you are working from a partial or blurred read."""

PAN_CARD_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.PAN.value,
    response_schema=PanCardRead,
    prompt=EXTRACT_PAN_PROMPT,
    field_keys_by_attribute={
        "name": "name",
        "parent_name": "parentName",
        "date_of_birth": "dob",
        "pan": "pan",
    },
    structure_keys_by_attribute={
        "photograph_present": "photo",
        "signature_present": "signature",
        "hologram_present": "hologram",
    },
)
