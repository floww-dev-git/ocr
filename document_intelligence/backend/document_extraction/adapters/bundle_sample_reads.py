"""Canned reads for the bundled deed files, carried from the sale deed prototype.

A real title bundle is one PDF holding a current deed photocopied together with the
prior deeds behind it. These four are fabricated over a single imaginary parcel —
Sy. No. 142/2, Plot 17, Kondapur — one per verdict the chain engine can return, so
a run can be judged right or wrong rather than merely "it produced something".

Carried from sale_deed_poc/build/poc/make_samples.py::build_bundles(). The PDFs the
officer attaches are generated from the same specs by scripts/make_deed_bundles.py,
so the offline read and the real read describe the same paper.
"""
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.adapters.deed_sample_reads import DeedSampleSpec
from document_extraction.adapters.sample_reads import (
    DocumentSampleRead,
    build_deed_sample_read,
)
from document_extraction.dtos.deed_record_dtos import PartyDTO

BUNDLE_APPLICATION_ID = "BN/2026/0455"
PAGES_PER_DEED = 2
DEED_TYPE_LABEL = "Sale Deed"

SUB_REGISTRAR_OFFICE = "SRO Serilingampally"
SURVEY_NUMBER = "142/2"
PLOT_NUMBER = "17"
VILLAGE = "Kondapur"
MANDAL = "Serilingampally"
DISTRICT = "Ranga Reddy"
# The four sides, stated separately because a deed prints them as a schedule. The
# one-string form a read reports is built from them, never parsed back out of it: a
# boundary description contains full stops of its own ("Plot No. 18"), so the prose
# cannot be split back into sides without cutting a value in half.
BOUNDARY_SIDES = (
    ("North", "Plot No. 18"),
    ("South", "Plot No. 16"),
    ("East", "30 feet wide road"),
    ("West", "Open land in Sy. No. 142/3"),
)
BOUNDARIES = " ".join(
    f"{side}: {description}." for side, description in BOUNDARY_SIDES
)
EXTENT_400_TEXT = "400 Sq. Yards (334.45 Sq. Metres)"
EXTENT_600_TEXT = "600 Sq. Yards (501.67 Sq. Metres)"

GOVIND = PartyDTO(
    name="Govind Rao",
    relation="s/o",
    relative_name="Narsimha Rao",
    address="H.No. 4-21, Gachibowli, Ranga Reddy District",
)
RAMESH = PartyDTO(
    name="Ramesh Kumar",
    relation="s/o",
    relative_name="Venkat Rao",
    address="Flat 302, Sai Residency, Madhapur, Hyderabad 500081",
)
SUNITA = PartyDTO(
    name="Sunita Sharma",
    relation="w/o",
    relative_name="Anil Sharma",
    address="12-3-45, Road No. 7, Jubilee Hills, Hyderabad 500033",
)
PRAKASH = PartyDTO(
    name="Prakash Iyer",
    relation="s/o",
    relative_name="Subramanian Iyer",
    address="Villa 9, Aparna Cyber Life, Nallagandla, Hyderabad 500019",
)
LAKSHMI = PartyDTO(
    name="Lakshmi Narayanan",
    relation="s/o",
    relative_name="Sundara Rajan",
    address="8-2-120, Banjara Hills, Hyderabad 500034",
)
# The same person, spelled the way a second sub-registrar transliterated it.
LAKSHMI_VARIANT = PartyDTO(
    name="Laxmi Narayan",
    relation="s/o",
    relative_name="Sundara Rajan",
    address="8-2-120, Banjara Hills, Hyderabad 500034",
)
# A stranger to the chain: he matches no prior buyer, yet his deed cites the
# chain's own 2011 deed as his source of title.
FAROOQ = PartyDTO(
    name="Mohammed Farooq",
    relation="s/o",
    relative_name="Abdul Rahman",
    address="16-1-8, Malakpet, Hyderabad 500036",
)

ROOT_DEED_NUMBER = "1188/2003"
SECOND_DEED_NUMBER = "2451/2011"
THIRD_DEED_NUMBER = "5820/2019"


def _deed(
    filename: str,
    document_type_id: str,
    doc_no: str,
    registration_date: str,
    execution_date: str,
    seller: PartyDTO,
    buyer: PartyDTO,
    extent_text: str,
    extent_sq_yard: float,
    consideration_text: str,
    consideration_inr: float,
    stamp_duty_text: str,
    estamp_no: str,
    prior_deed_refs: Tuple[str, ...],
    type_confidence: float,
) -> DeedSampleSpec:
    return DeedSampleSpec(
        application_id=BUNDLE_APPLICATION_ID,
        document_type_id=document_type_id,
        filename=filename,
        file_format="PDF",
        file_size_bytes=0,
        type_confidence=type_confidence,
        page_count=PAGES_PER_DEED,
        doc_no=doc_no,
        registration_date=registration_date,
        sro=SUB_REGISTRAR_OFFICE,
        vendor=seller.name,
        purchaser=buyer.name,
        survey_no=SURVEY_NUMBER,
        plot_no=PLOT_NUMBER,
        extent_text=extent_text,
        extent_sq_yard=extent_sq_yard,
        village=VILLAGE,
        consideration_text=consideration_text,
        consideration_inr=consideration_inr,
        boundaries=BOUNDARIES,
        prior_deed_refs=prior_deed_refs,
        vendor_party=seller,
        purchaser_party=buyer,
        execution_date=execution_date,
        stamp_duty_text=stamp_duty_text,
        estamp_no=estamp_no,
    )


def _root_deed(filename: str) -> DeedSampleSpec:
    """The mother deed: an assigned patta holder sells in, so it cites no prior deed."""
    return _deed(
        filename=filename,
        document_type_id=DocumentTypeEnum.LINK_DOCUMENT.value,
        doc_no=ROOT_DEED_NUMBER,
        registration_date="2003-06-12",
        execution_date="2003-06-05",
        seller=GOVIND,
        buyer=RAMESH,
        extent_text=EXTENT_400_TEXT,
        extent_sq_yard=400.0,
        consideration_text="Rs. 6,00,000/- (Rupees Six Lakhs only)",
        consideration_inr=600000.0,
        stamp_duty_text="Rs. 36,000/-",
        estamp_no="IN-TS41882003116742K",
        prior_deed_refs=(),
        type_confidence=0.93,
    )


def _second_deed(filename: str, buyer: PartyDTO) -> DeedSampleSpec:
    return _deed(
        filename=filename,
        document_type_id=DocumentTypeEnum.LINK_DOCUMENT.value,
        doc_no=SECOND_DEED_NUMBER,
        registration_date="2011-09-05",
        execution_date="2011-09-02",
        seller=RAMESH,
        buyer=buyer,
        extent_text=EXTENT_400_TEXT,
        extent_sq_yard=400.0,
        consideration_text="Rs. 42,00,000/- (Rupees Forty Two Lakhs only)",
        consideration_inr=4200000.0,
        stamp_duty_text="Rs. 2,52,000/-",
        estamp_no="IN-TS62445201193318L",
        prior_deed_refs=(ROOT_DEED_NUMBER,),
        type_confidence=0.95,
    )


def _third_deed(
    filename: str, seller: PartyDTO, extent_sq_yard: float, extent_text: str
) -> DeedSampleSpec:
    """The deed being relied on, so this is the one the catalog calls a sale deed."""
    return _deed(
        filename=filename,
        document_type_id=DocumentTypeEnum.SALE_DEED.value,
        doc_no=THIRD_DEED_NUMBER,
        registration_date="2019-02-18",
        execution_date="2019-02-11",
        seller=seller,
        buyer=PRAKASH,
        extent_text=extent_text,
        extent_sq_yard=extent_sq_yard,
        consideration_text="Rs. 96,00,000/- (Rupees Ninety Six Lakhs only)",
        consideration_inr=9600000.0,
        stamp_duty_text="Rs. 5,76,000/-",
        estamp_no="IN-TS80917201947725M",
        prior_deed_refs=(SECOND_DEED_NUMBER,),
        type_confidence=0.98,
    )


@dataclass(frozen=True)
class BundleSegmentRead:
    """One document inside a bundle: where it sits, and what reading it gives."""

    document_type_id: str
    page_start: int
    page_end: int
    summary: str
    sample_read: DocumentSampleRead
    is_title_doc: bool = True


@dataclass(frozen=True)
class BundleSampleRead:
    filename: str
    file_format: str
    type_confidence: float
    document_type_id: str
    headline: str
    segments: Tuple[BundleSegmentRead, ...]

    @property
    def page_count(self) -> int:
        return sum(
            segment.page_end - segment.page_start + 1 for segment in self.segments
        )


@dataclass(frozen=True)
class BundleSpec:
    """What a bundle is engineered to prove, and the deeds that prove it.

    The expected verdicts are part of the fixture, not a comment about it: they are
    asserted against the real chain engine, so editing a name or an extent here makes
    the bundle stop proving its scenario in a test rather than silently in a demo.
    """

    filename: str
    headline: str
    deeds: Tuple[DeedSampleSpec, ...]
    expected_overall: str
    expected_links: Tuple[str, ...]


def _summarise(deed: DeedSampleSpec) -> str:
    year = deed.registration_date[:4]
    return f"{year} sale: {deed.vendor} -> {deed.purchaser}"


def _build_bundle_sample_read(spec: BundleSpec) -> BundleSampleRead:
    """Pages fall out of the order of the deeds: each is rendered on two pages."""
    segments = tuple(
        BundleSegmentRead(
            document_type_id=deed.document_type_id,
            page_start=index * PAGES_PER_DEED,
            page_end=index * PAGES_PER_DEED + PAGES_PER_DEED - 1,
            summary=_summarise(deed),
            sample_read=build_deed_sample_read(deed),
        )
        for index, deed in enumerate(spec.deeds)
    )
    return BundleSampleRead(
        filename=spec.filename,
        file_format="PDF",
        # The file itself is plainly a title bundle; which deed inside it is the
        # current one is what segmentation answers.
        type_confidence=0.94,
        document_type_id=DocumentTypeEnum.SALE_DEED.value,
        headline=spec.headline,
        segments=segments,
    )


CLEAN_CHAIN_FILENAME = "01_clean_chain.pdf"
WEAK_TRANSLITERATION_FILENAME = "02_weak_transliteration.pdf"
GAP_EXTENT_OVERFLOW_FILENAME = "03_gap_extent_overflow.pdf"
BROKEN_STRANGER_SELLER_FILENAME = "04_broken_stranger_seller.pdf"

# The chain vocabulary, restated as plain strings. Reading it from the chain engine
# would point this app at document_scrutiny, which depends on this one. A test pins
# every value below against the real enum, so a typo cannot slip through.
LINK_LINKED = "linked"
LINK_WEAK = "weak"
LINK_GAP = "gap"
LINK_BROKEN = "broken"
OVERALL_INTACT = "intact"
OVERALL_REVIEW = "review"
OVERALL_BROKEN = "broken"


def build_bundle_specs() -> Tuple[BundleSpec, ...]:
    """Four bundles over the same parcel — one per link verdict the chain can return."""
    return (
        BundleSpec(
            filename=CLEAN_CHAIN_FILENAME,
            headline=(
                "Unbroken chain: every seller is the previous buyer, extents and "
                "recitals agree."
            ),
            deeds=(
                _root_deed(CLEAN_CHAIN_FILENAME),
                _second_deed(CLEAN_CHAIN_FILENAME, buyer=SUNITA),
                _third_deed(
                    CLEAN_CHAIN_FILENAME,
                    seller=SUNITA,
                    extent_sq_yard=400.0,
                    extent_text=EXTENT_400_TEXT,
                ),
            ),
            expected_overall=OVERALL_INTACT,
            expected_links=(LINK_LINKED, LINK_LINKED),
        ),
        BundleSpec(
            filename=WEAK_TRANSLITERATION_FILENAME,
            headline=(
                "Same chain, but the last seller's name is transliterated "
                "differently ('Lakshmi Narayanan' -> 'Laxmi Narayan') — a caveat "
                "for a human, not a break."
            ),
            deeds=(
                _root_deed(WEAK_TRANSLITERATION_FILENAME),
                _second_deed(WEAK_TRANSLITERATION_FILENAME, buyer=LAKSHMI),
                _third_deed(
                    WEAK_TRANSLITERATION_FILENAME,
                    seller=LAKSHMI_VARIANT,
                    extent_sq_yard=400.0,
                    extent_text=EXTENT_400_TEXT,
                ),
            ),
            expected_overall=OVERALL_REVIEW,
            expected_links=(LINK_LINKED, LINK_WEAK),
        ),
        BundleSpec(
            filename=GAP_EXTENT_OVERFLOW_FILENAME,
            headline=(
                "Sells more than she owns: bought 400 sq.yd in 2011, conveys 600 "
                "sq.yd in 2019 — the extra 200 sq.yd has no source deed in the bundle."
            ),
            deeds=(
                _root_deed(GAP_EXTENT_OVERFLOW_FILENAME),
                _second_deed(GAP_EXTENT_OVERFLOW_FILENAME, buyer=SUNITA),
                _third_deed(
                    GAP_EXTENT_OVERFLOW_FILENAME,
                    seller=SUNITA,
                    extent_sq_yard=600.0,
                    extent_text=EXTENT_600_TEXT,
                ),
            ),
            expected_overall=OVERALL_REVIEW,
            expected_links=(LINK_LINKED, LINK_GAP),
        ),
        BundleSpec(
            filename=BROKEN_STRANGER_SELLER_FILENAME,
            headline=(
                "A stranger sells: the 2019 vendor was never a buyer in this chain, "
                "yet his deed cites 2451/2011 as his source of title."
            ),
            deeds=(
                _root_deed(BROKEN_STRANGER_SELLER_FILENAME),
                _second_deed(BROKEN_STRANGER_SELLER_FILENAME, buyer=SUNITA),
                _third_deed(
                    BROKEN_STRANGER_SELLER_FILENAME,
                    seller=FAROOQ,
                    extent_sq_yard=400.0,
                    extent_text=EXTENT_400_TEXT,
                ),
            ),
            expected_overall=OVERALL_BROKEN,
            expected_links=(LINK_LINKED, LINK_BROKEN),
        ),
    )


BUNDLE_SPECS: Tuple[BundleSpec, ...] = build_bundle_specs()

# Keyed by filename, not by application: a bundle is a file, and the officer picks
# which of the four histories to attach by picking which file to attach.
BUNDLE_SAMPLE_READS_BY_FILENAME: Mapping[str, BundleSampleRead] = {
    spec.filename: _build_bundle_sample_read(spec) for spec in BUNDLE_SPECS
}


def get_bundle_sample_read(filename: str) -> Optional[BundleSampleRead]:
    return BUNDLE_SAMPLE_READS_BY_FILENAME.get(str(filename or ""))


def get_bundle_segment_read(
    filename: str, page_start: Optional[int]
) -> Optional[BundleSegmentRead]:
    """The one document that begins on this page of this bundle."""
    bundle = get_bundle_sample_read(filename=filename)
    if bundle is None or page_start is None:
        return None
    for segment in bundle.segments:
        if segment.page_start == page_start:
            return segment
    return None
