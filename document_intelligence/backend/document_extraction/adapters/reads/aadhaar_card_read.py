from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class AadhaarCardRead(BaseModel):
    name: Optional[str] = Field(
        default=None,
        description=(
            "Cardholder name in ENGLISH exactly as printed. An Aadhaar prints the "
            "name twice, once in English and once in a regional script; give the "
            "English one."
        ),
    )
    date_of_birth: Optional[str] = Field(
        default=None,
        description=(
            "Date of birth as ISO yyyy-mm-dd. An Aadhaar prints dd/mm/yyyy, and "
            "sometimes only a year of birth"
        ),
    )
    gender: Optional[str] = Field(
        default=None, description="Gender as printed: Male, Female or Other"
    )
    aadhaar_number: Optional[str] = Field(
        default=None,
        description="The twelve-digit Aadhaar number, digits only, no spaces",
    )
    address: Optional[str] = Field(
        default=None,
        description=(
            "Full address as printed on the reverse, as one line, including the "
            "PIN code"
        ),
    )
    photograph_present: bool = Field(
        default=True, description="True if a photograph is printed on the card"
    )
    qr_present: bool = Field(
        default=True, description="True if the QR code is visible on the card"
    )
    emblem_present: bool = Field(
        default=True,
        description="True if the Government of India national emblem is printed",
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


EXTRACT_AADHAAR_PROMPT = """These images are the pages of ONE Indian Aadhaar card issued by the
Unique Identification Authority of India. The pages may be scanned, photographed, low-contrast,
rotated, or show only one side of the card.

Read it into the response schema:
- name: the holder's name in ENGLISH exactly as printed, preserving its capitalisation. The card
  prints the name in English and again in a regional script (Telugu, Hindi, Tamil and others);
  transliterate only if the English line is genuinely absent.
- date_of_birth: normalise to ISO yyyy-mm-dd. The card prints dd/mm/yyyy. Some older cards print
  only a year of birth, sometimes labelled 'Year of Birth' — in that case give yyyy-01-01 and say
  so in low_confidence_fields.
- gender: Male, Female or Other, as printed.
- aadhaar_number: the twelve digits only, with the spaces removed. It is printed in three groups
  of four. Do not confuse it with the longer Virtual ID or the enrolment number.
- address: the address block printed on the reverse, as a single line, keeping the PIN code.
- photograph_present, qr_present, emblem_present: whether each is actually visible. Report false
  only when you can see that side of the card and the element is genuinely absent. If you were
  given only the front, leave the reverse-only elements true rather than guessing they are missing.
- confidence: your overall confidence in this read, 0 to 1.
- low_confidence_fields: the labels of any fields you are unsure about, so a human can check
  them. Use the labels 'name', 'dob', 'gender', 'aadhaarNo', 'address'.
- boxes: for each field you read, where you read it from. Use the same labels, and give the box
  as [ymin, xmin, ymax, xmax] normalised to 0-1000 on that page, with a 0-based page index.

Do not guess a value you cannot see. Leave a field null rather than inventing it, and say so in
low_confidence_fields when you are working from a partial or blurred read."""

AADHAAR_CARD_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.AADHAAR.value,
    response_schema=AadhaarCardRead,
    prompt=EXTRACT_AADHAAR_PROMPT,
    field_keys_by_attribute={
        "name": "name",
        "date_of_birth": "dob",
        "gender": "gender",
        "aadhaar_number": "aadhaarNo",
        "address": "address",
    },
    structure_keys_by_attribute={
        "photograph_present": "photo",
        "qr_present": "qr",
        "emblem_present": "emblem",
    },
)
