from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.gemini_schemas import FieldBoxRead
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class DrivingLicenceRead(BaseModel):
    name: Optional[str] = Field(
        default=None, description="Holder name in ENGLISH exactly as printed"
    )
    date_of_birth: Optional[str] = Field(
        default=None, description="Date of birth as ISO yyyy-mm-dd"
    )
    licence_number: Optional[str] = Field(
        default=None,
        description=(
            "The licence number, spaces and hyphens removed, as in 'TS0920150012345'"
        ),
    )
    valid_until: Optional[str] = Field(
        default=None,
        description=(
            "The date the licence runs to, as ISO yyyy-mm-dd. Printed as 'Valid Till' "
            "or 'NT Valid Till'"
        ),
    )
    address: Optional[str] = Field(
        default=None, description="Full address as printed, as one line, with the PIN"
    )
    blood_group: Optional[str] = Field(
        default=None, description="Blood group as printed, e.g. 'B+'"
    )
    photograph_present: bool = Field(
        default=True, description="True if a photograph is printed on the licence"
    )
    hologram_present: bool = Field(
        default=True, description="True if the hologram is visible on the licence"
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


EXTRACT_DRIVING_LICENCE_PROMPT = """These images are the pages of ONE Indian driving licence
issued by a State Transport Department. It may be the credit-card style smart card or the older
booklet, printed on one or both sides, and the pages may be scanned, photographed, low-contrast
or rotated.

Read it into the response schema:
- name: the holder's name in ENGLISH exactly as printed, preserving its capitalisation.
- date_of_birth: normalise to ISO yyyy-mm-dd. The licence prints dd-mm-yyyy.
- licence_number: the licence number with spaces and hyphens removed. It reads as a two-letter
  state code, then the issuing RTO number, then the year of issue, then a serial —
  'TS0920150012345', sometimes printed 'TS-09 20150012345'. Do NOT return the separate
  seven-digit or ten-digit 'Old licence number' if both appear.
- valid_until: the date the licence runs to, as ISO yyyy-mm-dd. It is printed as 'Valid Till'.
  A licence often prints TWO validity dates, one for transport vehicles ('NT Valid Till' or
  'Valid Till (NT)') and one for non-transport; give the NON-TRANSPORT date, which is the later
  one. If only one is printed, give that.
- address: the address block as a single line, keeping the PIN code.
- blood_group: as printed, e.g. 'B+', 'O-'. Leave null if it is not printed.
- photograph_present, hologram_present: whether each is actually visible. Report false only when
  you can see that side and the element is genuinely absent.
- confidence: your overall confidence in this read, 0 to 1.
- low_confidence_fields: the labels of any fields you are unsure about, so a human can check
  them. Use the labels 'name', 'dob', 'dlNo', 'validUpto', 'address', 'bloodGroup'.
- boxes: for each field you read, where you read it from. Use the same labels, and give the box
  as [ymin, xmin, ymax, xmax] normalised to 0-1000 on that page, with a 0-based page index.

Do not guess a value you cannot see. Leave a field null rather than inventing it, and say so in
low_confidence_fields when you are working from a partial or blurred read."""

DRIVING_LICENCE_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.DRIVING_LICENCE.value,
    response_schema=DrivingLicenceRead,
    prompt=EXTRACT_DRIVING_LICENCE_PROMPT,
    field_keys_by_attribute={
        "name": "name",
        "date_of_birth": "dob",
        "licence_number": "dlNo",
        "valid_until": "validUpto",
        "address": "address",
        "blood_group": "bloodGroup",
    },
    structure_keys_by_attribute={
        "photograph_present": "photo",
        "hologram_present": "hologram",
    },
)
