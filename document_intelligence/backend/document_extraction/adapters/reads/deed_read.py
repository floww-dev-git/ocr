from typing import List, Optional

from pydantic import BaseModel, Field

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.reads.deed_record_mapper import DeedRecordMapper
from document_extraction.dtos.read_spec_dtos import DocumentReadSpec


class DeedPartyRead(BaseModel):
    name: str = Field(
        description=(
            "Full name in ENGLISH — romanise/transliterate if the document is in "
            "another script (Tamil/Telugu/etc.)"
        )
    )
    name_original: Optional[str] = Field(
        default=None,
        description="Name exactly as written in the document's own script, if it is non-English",
    )
    relation: Optional[str] = Field(
        default=None, description="Relation marker, e.g. 's/o', 'w/o', 'd/o'"
    )
    relative_name: Optional[str] = Field(
        default=None,
        description="Father's/husband's name (English) used for disambiguation",
    )
    address: Optional[str] = None
    pan: Optional[str] = Field(
        default=None, description="PAN if printed, format like 'ABCDE1234F'"
    )
    aadhaar: Optional[str] = Field(
        default=None,
        description="Aadhaar number or any other government ID if present",
    )


class DeedPropertyRead(BaseModel):
    survey_no: Optional[str] = None
    plot_no: Optional[str] = None
    extent_text: Optional[str] = Field(
        default=None, description="Extent exactly as written, e.g. '300 sq. yards'"
    )
    extent_sqyd: Optional[float] = Field(
        default=None,
        description="Extent normalised to square yards if determinable",
    )
    boundaries: Optional[str] = Field(
        default=None, description="Boundary schedule N/S/E/W as a single string"
    )
    locality: Optional[str] = Field(
        default=None, description="Village / mandal / district / city"
    )
    ulpin: Optional[str] = Field(
        default=None, description="ULPIN / Bhu-Aadhaar if present"
    )


class DeedFieldBoxRead(BaseModel):
    """Where on the page a key value was read from — for click-to-verify provenance."""

    label: str = Field(
        description=(
            "Which field, e.g. 'doc_no', 'seller', 'buyer', 'consideration', "
            "'survey_no', 'registration_date'"
        )
    )
    value: str = Field(description="The value as read")
    page: int = Field(default=0, description="0-based page index the value appears on")
    box: List[int] = Field(
        default_factory=list,
        description="[ymin, xmin, ymax, xmax] normalised to 0-1000 on that page",
    )


class DeedRead(BaseModel):
    """One sale deed, extracted into structured form."""

    doc_no: Optional[str] = Field(
        default=None, description="Registration document number, e.g. '2451/2007'"
    )
    sro: Optional[str] = Field(default=None, description="Sub-Registrar Office")
    registration_date: Optional[str] = Field(
        default=None, description="Registration date, ISO yyyy-mm-dd if determinable"
    )
    execution_date: Optional[str] = None
    deed_type: Optional[str] = Field(
        default=None,
        description=(
            "e.g. 'Sale Deed', 'Gift Deed', 'GPA', 'Agreement to Sell', "
            "'Partition', 'Will'"
        ),
    )
    sellers: List[DeedPartyRead] = Field(
        default_factory=list, description="Vendor(s) / transferor(s)"
    )
    buyers: List[DeedPartyRead] = Field(
        default_factory=list, description="Vendee(s) / transferee(s)"
    )
    property: DeedPropertyRead = Field(default_factory=DeedPropertyRead)
    consideration_text: Optional[str] = Field(
        default=None, description="Consideration amount as written"
    )
    consideration_inr: Optional[float] = Field(
        default=None, description="Consideration normalised to INR if determinable"
    )
    stamp_duty_text: Optional[str] = None
    estamp_no: Optional[str] = Field(
        default=None, description="e-Stamp certificate number if present"
    )
    prior_deed_refs: List[str] = Field(
        default_factory=list,
        description=(
            "Document numbers cited in the recital as the seller's source of "
            "title, e.g. ['1234/1998']"
        ),
    )
    executed_via_gpa: bool = Field(
        default=False,
        description=(
            "True if executed by a power-of-attorney holder rather than the owner"
        ),
    )
    schedule_present: bool = Field(
        default=True,
        description="True if a 'Schedule of Property' section is present",
    )
    stamp_endorsement_present: bool = Field(
        default=True, description="True if a stamp duty endorsement is present"
    )
    registration_endorsement_present: bool = Field(
        default=True,
        description="True if the sub-registrar's registration endorsement is present",
    )
    witnesses_present: bool = Field(
        default=True, description="True if witness signatures are present"
    )
    confidence: float = Field(
        default=0.0, description="Overall extraction confidence 0..1"
    )
    low_confidence_fields: List[str] = Field(
        default_factory=list,
        description="Field names the model is unsure about, for human review",
    )
    boxes: List[DeedFieldBoxRead] = Field(
        default_factory=list,
        description=(
            "Provenance boxes for key fields (doc_no, seller, buyer, "
            "consideration, survey_no, registration_date)"
        ),
    )


# Carried verbatim from sale_deed_poc/build/poc/extract.py. The conversion factors
# and the Schedule-of-Property instruction are the parts that earn their keep: a
# generic prompt reads the extent off the wrong paragraph.
EXTRACT_DEED_PROMPT = """These pages are ONE registered Indian property document. Read it into the response \
schema as faithfully as possible. The pages may be scanned, photographed, multilingual (English / Telugu / \
Kannada / Hindi / Marathi / Tamil), and contain handwritten endorsements.

- Identify the deed_type precisely. If it is NOT a registered sale (e.g. a GPA / Power of Attorney, an \
Agreement to Sell, a Will, a Gift, or a Partition), say so in deed_type — this matters legally.
- NAMES: always give `name` in ENGLISH (transliterate from Tamil/Telugu/etc.), and put the name exactly as \
written in the original script into `name_original`. Capture the relation marker (s/o, w/o, d/o) and the \
relative's name — these disambiguate people across deeds.
- CRUCIAL IDENTIFIERS — capture carefully when present: PAN (format like 'ABCDE1234F'), Aadhaar / any government ID \
(into `aadhaar`), survey number and plot number, document/registration number, SRO, and the registration \
and execution dates (ISO yyyy-mm-dd).
- For property, give extent exactly as written in extent_text, and ALSO normalise to square yards in \
extent_sqyd when you can (1 acre = 4840 sq yd, 1 sq m = 1.196 sq yd, 1 sq ft = 0.111 sq yd). The property \
details often sit in a 'Schedule of Property' section — read it.
- prior_deed_refs: list every prior document number cited as the seller's source of title (the recital / \
"flow of title"). Format like '1234/1998'.
- Set executed_via_gpa=true if a power-of-attorney holder signed on behalf of the owner.
- PROVENANCE: in `boxes`, for each of these key fields you find — doc_no, seller, buyer, consideration, \
survey_no, registration_date — return one entry with the field label, the value, the 0-based page index it \
appears on (relative to the pages you were given), and its bounding box as [ymin, xmin, ymax, xmax] \
normalised to 0-1000 on that page.
- confidence: your overall confidence 0..1. low_confidence_fields: name any field you are unsure about.
Do not invent values. Use null when a field is genuinely absent.
- Also report whether each of these is present on the paper: a 'Schedule of Property' section \
(schedule_present), a stamp duty endorsement (stamp_endorsement_present), the sub-registrar's registration \
endorsement (registration_endorsement_present), and witness signatures (witnesses_present). Report false \
only when you can see the relevant part of the document and it is genuinely absent."""

_DEED_STRUCTURE_KEYS = {
    "schedule_present": "schedule",
    "stamp_endorsement_present": "stamp",
    "registration_endorsement_present": "registration",
    "witnesses_present": "witnesses",
}

# The reading is nested, so the catalog's flat field keys are reached by path.
_SHARED_FIELD_KEYS = {
    "doc_no": "docNo",
    "registration_date": "regDate",
    "sro": "sro",
    "sellers.0.name": "vendor",
    "buyers.0.name": "purchaser",
    "property.survey_no": "surveyNo",
    "property.plot_no": "plotNo",
    "property.extent_text": "extent",
    "property.locality": "village",
}

SALE_DEED_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.SALE_DEED.value,
    response_schema=DeedRead,
    prompt=EXTRACT_DEED_PROMPT,
    field_keys_by_attribute={
        **_SHARED_FIELD_KEYS,
        "consideration_text": "consideration",
        "property.boundaries": "boundaries",
    },
    structure_keys_by_attribute=_DEED_STRUCTURE_KEYS,
    record_mapper=DeedRecordMapper,
    bundleable=True,
)

# A link document is the same paper read the same way; the catalog simply declares
# fewer fields on it, because the consideration on a prior owner's purchase is not
# this application's business.
LINK_DOCUMENT_READ = DocumentReadSpec(
    document_type_id=DocumentTypeEnum.LINK_DOCUMENT.value,
    response_schema=DeedRead,
    prompt=EXTRACT_DEED_PROMPT,
    field_keys_by_attribute=dict(_SHARED_FIELD_KEYS),
    structure_keys_by_attribute={
        key: value
        for key, value in _DEED_STRUCTURE_KEYS.items()
        if value != "witnesses"
    },
    record_mapper=DeedRecordMapper,
    bundleable=True,
)
