"""Deed record contract — the boundary between extraction (AI) and chain logic (code).

These pydantic models are used two ways:
1. as Gemini's structured-output `response_schema` (the AI fills them in), and
2. as the typed input to the deterministic chain engine.

Keeping one schema for both means the AI/code boundary is explicit and can't drift.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Party(BaseModel):
    name: str = Field(description="Full name in ENGLISH — romanise/transliterate if the document is in another script (Tamil/Telugu/etc.)")
    name_original: str | None = Field(default=None, description="Name exactly as written in the document's own script, if it is non-English")
    relation: str | None = Field(default=None, description="Relation marker, e.g. 's/o', 'w/o', 'd/o'")
    relative_name: str | None = Field(default=None, description="Father's/husband's name (English) used for disambiguation")
    address: str | None = None
    pan: str | None = Field(default=None, description="PAN if printed, format like 'ABCDE1234F'")
    aadhaar: str | None = Field(default=None, description="Aadhaar number or any other government ID if present")


class PropertyInfo(BaseModel):
    survey_no: str | None = None
    plot_no: str | None = None
    extent_text: str | None = Field(default=None, description="Extent exactly as written, e.g. '300 sq. yards'")
    extent_sqyd: float | None = Field(default=None, description="Extent normalised to square yards if determinable")
    boundaries: str | None = Field(default=None, description="Boundary schedule N/S/E/W as a single string")
    locality: str | None = Field(default=None, description="Village / mandal / district / city")
    ulpin: str | None = Field(default=None, description="ULPIN / Bhu-Aadhaar if present")


class FieldBox(BaseModel):
    """Where on the page a key value was read from — for click-to-verify provenance."""
    label: str = Field(description="Which field, e.g. 'doc_no', 'seller', 'buyer', 'consideration', 'survey_no', 'registration_date'")
    value: str = Field(description="The value as read")
    page: int = Field(default=0, description="0-based page index the value appears on")
    box: list[int] = Field(default_factory=list, description="[ymin, xmin, ymax, xmax] normalised to 0-1000 on that page")


class DeedRecord(BaseModel):
    """One sale deed, extracted into structured form."""
    doc_no: str | None = Field(default=None, description="Registration document number, e.g. '2451/2007'")
    sro: str | None = Field(default=None, description="Sub-Registrar Office")
    registration_date: str | None = Field(default=None, description="Registration date, ISO yyyy-mm-dd if determinable")
    execution_date: str | None = None
    deed_type: str | None = Field(default=None, description="e.g. 'Sale Deed', 'Gift Deed', 'GPA', 'Agreement to Sell', 'Partition', 'Will'")
    sellers: list[Party] = Field(default_factory=list, description="Vendor(s) / transferor(s)")
    buyers: list[Party] = Field(default_factory=list, description="Vendee(s) / transferee(s)")
    property: PropertyInfo = Field(default_factory=PropertyInfo)
    consideration_text: str | None = Field(default=None, description="Consideration amount as written")
    consideration_inr: float | None = Field(default=None, description="Consideration normalised to INR if determinable")
    stamp_duty_text: str | None = None
    estamp_no: str | None = Field(default=None, description="e-Stamp certificate number if present")
    prior_deed_refs: list[str] = Field(
        default_factory=list,
        description="Document numbers cited in the recital as the seller's source of title, e.g. ['1234/1998']",
    )
    executed_via_gpa: bool = Field(default=False, description="True if executed by a power-of-attorney holder rather than the owner")
    confidence: float = Field(default=0.0, description="Overall extraction confidence 0..1")
    low_confidence_fields: list[str] = Field(
        default_factory=list, description="Field names the model is unsure about, for human review"
    )
    boxes: list[FieldBox] = Field(
        default_factory=list, description="Provenance boxes for key fields (doc_no, seller, buyer, consideration, survey_no, registration_date)"
    )

    # multi-document segmentation: a single uploaded file may bundle several deeds
    page_start: int | None = Field(default=None, description="0-based first page of this document within the uploaded file")
    page_end: int | None = Field(default=None, description="0-based last page (inclusive) of this document within the file")
    doc_role: str | None = Field(default=None, description="'primary' for the main/most-recent sale deed; 'link' for a bundled prior/related document")

    # populated by the pipeline, not the model
    source_filename: str | None = None
    deed_id: str | None = None


class DocSegment(BaseModel):
    """One document located inside an uploaded file by the fast inventory pass."""
    doc_type: str = Field(description="e.g. 'Sale Deed', 'GPA', 'Encumbrance Certificate', 'Partition Deed', 'Gift Deed', 'Link Document'")
    page_start: int = Field(description="0-based first page of this document within the file")
    page_end: int = Field(description="0-based last page (inclusive)")
    summary: str | None = Field(default=None, description="One-line description, e.g. '2021 sale: A. Kumar → B. Sharma'")
    language: str | None = Field(default=None, description="Primary language of the document")
    is_title_doc: bool = Field(default=True, description="True if it is a title-conveying deed (sale/gift/partition); False for EC/tax/supporting docs")


class FileInventory(BaseModel):
    """The result of the fast first-pass scan of one uploaded file."""
    documents: list[DocSegment] = Field(default_factory=list, description="Each distinct registered document found in the file, in page order")


class PageLabel(BaseModel):
    """Per-page boundary signal used to segment a bundled file into documents."""
    page: int = Field(description="0-based page index")
    starts_new_document: bool = Field(description="True if a NEW registered document begins on this page")
    doc_type: str | None = Field(default=None, description="Document type if this page starts one, e.g. 'Sale Deed', 'Partition Deed', 'GPA', 'Registration Summary'")
    doc_no: str | None = Field(default=None, description="Document/registration number if visible")
    summary: str | None = Field(default=None, description="One-line description if this page starts a document")


class PageMap(BaseModel):
    """Per-page classification of one uploaded file, in page order."""
    pages: list[PageLabel] = Field(default_factory=list)


# ---- verdict vocabulary (shared by chain.py and the frontend) ----

LINK_LINKED = "linked"        # clean
LINK_WEAK = "weak"            # passes but with a caveat (e.g. transliteration)
LINK_GAP = "gap"             # a deed appears to be missing
LINK_BROKEN = "broken"       # no continuity at all

OVERALL_INTACT = "intact"
OVERALL_REVIEW = "review"     # intact-with-warnings
OVERALL_BROKEN = "broken"

SEV_HIGH = "high"
SEV_MEDIUM = "medium"
SEV_LOW = "low"
SEV_CLEAR = "clear"
