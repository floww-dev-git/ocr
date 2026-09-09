"""Generate synthetic deed bundles as PDFs, for driving the full upload -> analyze -> verdict path.

Why this exists: the pipeline needs real documents, and real title bundles are private. These are
fabricated deeds for engineered chains whose verdicts are known in advance, so a run can be judged
right or wrong rather than merely "it produced something".

Each bundle is ONE PDF holding several registered documents back to back (a stamp-paper header and a
fresh 'SALE DEED' title start every one) so the inventory pass in `extract.py` has real boundaries to
segment on, exactly as a real link-document bundle would.

    python3 make_samples.py            # -> samples/

The expected verdict of every bundle is asserted against the real chain engine in `test_samples.py`;
the two read the same specs, so a fixture can never silently drift from what it claims to prove.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from schema import (
    DeedRecord, Party, PropertyInfo,
    LINK_LINKED, LINK_WEAK, LINK_GAP, LINK_BROKEN,
    OVERALL_INTACT, OVERALL_REVIEW, OVERALL_BROKEN,
)

BASE = Path(__file__).parent
OUT_DIR = BASE / "samples"

PAGE_W, PAGE_H = 1240, 1754           # A4 at 150 dpi
MARGIN = 96
BODY_W = PAGE_W - 2 * MARGIN
DPI = 150.0

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
FONT_BODY = FONT_DIR / "DejaVuSerif.ttf"
FONT_BODY_BOLD = FONT_DIR / "DejaVuSerif-Bold.ttf"
FONT_TITLE = FONT_DIR / "DejaVuSans-Bold.ttf"
FONT_MONO = FONT_DIR / "DejaVuSansMono.ttf"

INK = 25            # near-black on white, like a clean scan
GREY = 90


class SampleGenerationError(RuntimeError):
    """Raised when a sample bundle cannot be rendered (missing fonts, unwritable output)."""


class ScenarioKind(Enum):
    """What a bundle is engineered to prove. Values mirror the link verdicts in `schema.py`."""
    CLEAN = "clean"
    WEAK = "weak"
    GAP = "gap"
    BROKEN = "broken"


@dataclass(frozen=True)
class PartySpec:
    name: str
    relation: str
    relative_name: str
    address: str
    age: int

    def as_party(self) -> Party:
        return Party(
            name=self.name,
            name_original=self.name,
            relation=self.relation,
            relative_name=self.relative_name,
            address=self.address,
            pan="",
            aadhaar="",
        )

    def render(self) -> str:
        return (f"{self.name}, {self.relation} {self.relative_name}, aged {self.age} years, "
                f"residing at {self.address}")


@dataclass(frozen=True)
class DeedSpec:
    doc_no: str
    sro: str
    execution_date: str          # dd-mm-yyyy, as printed on the deed
    registration_date: str       # dd-mm-yyyy, as printed on the deed
    registration_iso: str        # yyyy-mm-dd, what extraction should normalise to
    deed_type: str
    seller: PartySpec
    buyer: PartySpec
    survey_no: str
    plot_no: str
    extent_sqyd: float
    extent_text: str
    boundaries: tuple[str, str, str, str]      # north, south, east, west
    locality: str
    consideration_inr: float
    consideration_text: str
    stamp_duty_text: str
    estamp_no: str
    prior_deed_refs: tuple[str, ...]
    prior_deed_date: str         # date of the cited prior deed; "" when this is the root
    book_volume: str

    def as_deed_record(self, deed_id: str, source_filename: str) -> DeedRecord:
        """The record the extractor should produce from this deed — the ground truth."""
        return DeedRecord(
            doc_no=self.doc_no,
            sro=self.sro,
            registration_date=self.registration_iso,
            execution_date=self.execution_date,
            deed_type=self.deed_type,
            sellers=[self.seller.as_party()],
            buyers=[self.buyer.as_party()],
            property=PropertyInfo(
                survey_no=self.survey_no,
                plot_no=self.plot_no,
                extent_text=self.extent_text,
                extent_sqyd=self.extent_sqyd,
                boundaries=" | ".join(self.boundaries),
                locality=self.locality,
                ulpin="",
            ),
            consideration_text=self.consideration_text,
            consideration_inr=self.consideration_inr,
            stamp_duty_text=self.stamp_duty_text,
            estamp_no=self.estamp_no,
            prior_deed_refs=list(self.prior_deed_refs),
            executed_via_gpa=False,
            confidence=1.0,
            low_confidence_fields=[],
            boxes=[],
            page_start=0,
            page_end=1,
            doc_role="primary",
            source_filename=source_filename,
            deed_id=deed_id,
        )


@dataclass(frozen=True)
class BundleSpec:
    filename: str
    scenario: str                        # ScenarioKind value
    headline: str
    expected_overall: str                # OVERALL_* from schema.py
    expected_links: tuple[str, ...]      # LINK_* per consecutive link, in date order
    deeds: tuple[DeedSpec, ...]


# --------------------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------------------

class PageWriter:
    """A cursor over one page image. Draws top-down and reports when the page is full."""

    def __init__(self, fonts: dict[str, ImageFont.FreeTypeFont]) -> None:
        self.image = Image.new("L", (PAGE_W, PAGE_H), color=255)
        self.draw = ImageDraw.Draw(self.image)
        self.fonts = fonts
        self.y = MARGIN

    def _wrap(self, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in text.split():
            trial = f"{current} {word}".strip()
            if not current or self.draw.textlength(trial, font=font) <= width:
                current = trial
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def gap(self, px: int) -> None:
        self.y += px

    def rule(self) -> None:
        self.draw.line([(MARGIN, self.y), (PAGE_W - MARGIN, self.y)], fill=GREY, width=2)
        self.y += 18

    def centered(self, text: str, font_key: str, fill: int = INK) -> None:
        font = self.fonts[font_key]
        w = self.draw.textlength(text, font=font)
        self.draw.text(((PAGE_W - w) / 2, self.y), text, font=font, fill=fill)
        self.y += font.size + 12

    def para(self, text: str, font_key: str = "body", indent: int = 0, fill: int = INK) -> None:
        font = self.fonts[font_key]
        for line in self._wrap(text, font, BODY_W - indent):
            self.draw.text((MARGIN + indent, self.y), line, font=font, fill=fill)
            self.y += font.size + 10

    def columns(self, left: str, right: str, font_key: str = "body") -> None:
        """Two side-by-side columns. Padding with spaces cannot work in a proportional font —
        and a collapsed signature block reads as one long name to the extractor."""
        font = self.fonts[font_key]
        self.draw.text((MARGIN, self.y), left, font=font, fill=INK)
        self.draw.text((MARGIN + BODY_W // 2, self.y), right, font=font, fill=INK)
        self.y += font.size + 10

    def kv(self, label: str, value: str, font_key: str = "body") -> None:
        font = self.fonts[font_key]
        bold = self.fonts["body_bold"]
        self.draw.text((MARGIN, self.y), label, font=bold, fill=INK)
        self.draw.text((MARGIN + 300, self.y), value, font=font, fill=INK)
        self.y += font.size + 10


def _load_fonts() -> dict[str, ImageFont.FreeTypeFont]:
    missing = [p.name for p in (FONT_BODY, FONT_BODY_BOLD, FONT_TITLE, FONT_MONO) if not p.exists()]
    if missing:
        raise SampleGenerationError(
            f"Missing DejaVu fonts {missing} in {FONT_DIR}. Install them with: "
            f"sudo apt-get install fonts-dejavu-core"
        )
    return {
        "body": ImageFont.truetype(str(FONT_BODY), 23),
        "body_bold": ImageFont.truetype(str(FONT_BODY_BOLD), 23),
        "small": ImageFont.truetype(str(FONT_BODY), 19),
        "title": ImageFont.truetype(str(FONT_TITLE), 44),
        "sub": ImageFont.truetype(str(FONT_TITLE), 26),
        "mono": ImageFont.truetype(str(FONT_MONO), 21),
    }


def _render_deed(deed: DeedSpec, fonts: dict[str, ImageFont.FreeTypeFont]) -> list[Image.Image]:
    """One deed -> two pages. Page 1 opens with the stamp header + title (the boundary cue the
    inventory pass segments on); page 2 carries the Schedule and the registration endorsement."""
    p1 = PageWriter(fonts)
    p1.centered("INDIA NON JUDICIAL", "sub", fill=GREY)
    p1.centered("GOVERNMENT OF TELANGANA", "sub", fill=GREY)
    p1.gap(6)
    p1.para(f"e-Stamp Certificate No. : {deed.estamp_no}", font_key="mono")
    p1.para(f"Stamp Duty Paid         : {deed.stamp_duty_text}", font_key="mono")
    p1.gap(14)
    p1.rule()
    p1.centered(deed.deed_type.upper(), "title")
    p1.rule()
    p1.gap(10)
    p1.kv("Document No.", deed.doc_no)
    p1.kv("Sub-Registrar Office", deed.sro)
    p1.kv("Date of Execution", deed.execution_date)
    p1.kv("Date of Registration", deed.registration_date)
    p1.gap(20)
    p1.para(f"This {deed.deed_type} is made and executed on this {deed.execution_date} BETWEEN:")
    p1.gap(14)
    p1.para("VENDOR:", font_key="body_bold")
    p1.para(deed.seller.render(), indent=40)
    p1.para("(hereinafter called the VENDOR, which expression shall include their heirs, "
            "executors, administrators and assigns)", indent=40, font_key="small")
    p1.gap(10)
    p1.para("AND", font_key="body_bold")
    p1.gap(10)
    p1.para("VENDEE:", font_key="body_bold")
    p1.para(deed.buyer.render(), indent=40)
    p1.para("(hereinafter called the VENDEE, which expression shall include their heirs, "
            "executors, administrators and assigns)", indent=40, font_key="small")
    p1.gap(24)

    if deed.prior_deed_refs:
        source = ", ".join(deed.prior_deed_refs)
        recital = (f"WHEREAS the Vendor is the sole and absolute owner and in peaceful possession of the "
                   f"property more fully described in the Schedule hereunder, having acquired the same "
                   f"under and by virtue of registered Sale Deed bearing Document No. {source} of the "
                   f"Sub-Registrar Office, {deed.sro}, dated {deed.prior_deed_date}.")
    else:
        recital = ("WHEREAS the Vendor is the sole and absolute owner and in peaceful possession of the "
                   "property more fully described in the Schedule hereunder, the same having been "
                   "assigned to the Vendor by the District Collector, Ranga Reddy District, under "
                   "Assignment Patta No. 118/1987 dated 14-08-1987, and the Vendor's name having been "
                   "duly mutated in the revenue records thereafter.")
    p1.para(recital)
    p1.gap(18)
    p1.para(f"AND WHEREAS the Vendee has offered to purchase the said property for a total "
            f"consideration of {deed.consideration_text}, which the Vendor has agreed to accept.")
    p1.gap(18)
    p1.para(f"NOW THIS DEED WITNESSETH that in consideration of the sum of {deed.consideration_text} "
            f"paid by the Vendee to the Vendor, the receipt of which the Vendor hereby acknowledges, "
            f"the Vendor doth hereby grant, convey, transfer and assure unto the Vendee the property "
            f"described in the Schedule hereunder, TO HAVE AND TO HOLD the same absolutely and forever, "
            f"free from all encumbrances, charges, liens, attachments and court proceedings.")

    p2 = PageWriter(fonts)
    p2.centered("SCHEDULE OF PROPERTY", "sub")
    p2.rule()
    p2.gap(10)
    p2.kv("Survey No.", deed.survey_no)
    p2.kv("Plot No.", deed.plot_no)
    p2.kv("Extent", deed.extent_text)
    p2.kv("Village / Locality", deed.locality)
    p2.gap(16)
    p2.para("Bounded by:", font_key="body_bold")
    north, south, east, west = deed.boundaries
    p2.para(f"North  :  {north}", indent=40, font_key="mono")
    p2.para(f"South  :  {south}", indent=40, font_key="mono")
    p2.para(f"East   :  {east}", indent=40, font_key="mono")
    p2.para(f"West   :  {west}", indent=40, font_key="mono")
    p2.gap(28)
    p2.para("IN WITNESS WHEREOF the Vendor and the Vendee have set their hands to this deed on the "
            "day, month and year first above written, in the presence of the witnesses below.")
    p2.gap(30)
    p2.para("WITNESSES:", font_key="body_bold")
    p2.para("1.  K. Srinivasa Rao, s/o K. Ramulu, Kondapur, Hyderabad", indent=40)
    p2.para("2.  M. Anitha, w/o M. Suresh, Gachibowli, Hyderabad", indent=40)
    p2.gap(40)
    p2.columns("(Signature)", "(Signature)", font_key="small")
    p2.columns(deed.seller.name, deed.buyer.name, font_key="body_bold")
    p2.columns("VENDOR", "VENDEE", font_key="small")
    p2.gap(36)
    p2.rule()
    p2.centered("REGISTRATION ENDORSEMENT", "sub")
    p2.gap(6)
    p2.para(f"Registered as Document No. {deed.doc_no}, {deed.book_volume}, in the office of the "
            f"Sub-Registrar, {deed.sro}, Ranga Reddy District, on {deed.registration_date}.",
            font_key="small")
    p2.gap(10)
    p2.para("Sd/- SUB-REGISTRAR", font_key="body_bold")
    p2.para(f"{deed.sro}", font_key="small")

    return [p1.image, p2.image]


def _save_pdf(pages: list[Image.Image], path: Path) -> None:
    if not pages:
        raise SampleGenerationError(f"Refusing to write {path.name}: no pages were rendered.")
    path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(path, "PDF", save_all=True, append_images=pages[1:], resolution=DPI)


# --------------------------------------------------------------------------------------
# the scenarios — one parcel, four histories
# --------------------------------------------------------------------------------------

SRO = "Serilingampally"
SURVEY_NO = "142/2"
PLOT_NO = "17"
LOCALITY = "Kondapur Village, Serilingampally Mandal, Ranga Reddy District"
BOUNDARIES = ("Plot No. 18", "Plot No. 16", "30 feet wide road", "Open land in Sy. No. 142/3")

GOVIND = PartySpec("Govind Rao", "s/o", "Narsimha Rao",
                   "H.No. 4-21, Gachibowli, Ranga Reddy District", 58)
RAMESH = PartySpec("Ramesh Kumar", "s/o", "Venkat Rao",
                   "Flat 302, Sai Residency, Madhapur, Hyderabad 500081", 47)
SUNITA = PartySpec("Sunita Sharma", "w/o", "Anil Sharma",
                   "12-3-45, Road No. 7, Jubilee Hills, Hyderabad 500033", 39)
PRAKASH = PartySpec("Prakash Iyer", "s/o", "Subramanian Iyer",
                    "Villa 9, Aparna Cyber Life, Nallagandla, Hyderabad 500019", 44)
# same person as LAKSHMI, spelled the way a second sub-registrar transliterated it
LAKSHMI = PartySpec("Lakshmi Narayanan", "s/o", "Sundara Rajan",
                    "8-2-120, Banjara Hills, Hyderabad 500034", 51)
LAKSHMI_VARIANT = PartySpec("Laxmi Narayan", "s/o", "Sundara Rajan",
                            "8-2-120, Banjara Hills, Hyderabad 500034", 51)
# a stranger to the chain — matches no prior buyer, yet claims the chain's own deed as his source
FAROOQ = PartySpec("Mohammed Farooq", "s/o", "Abdul Rahman",
                   "16-1-8, Malakpet, Hyderabad 500036", 55)

EXTENT_400 = "400 Sq. Yards (334.45 Sq. Metres)"
EXTENT_600 = "600 Sq. Yards (501.67 Sq. Metres)"


def _root_deed() -> DeedSpec:
    """The mother deed: an assigned patta holder sells in — the chain's root, cites no prior deed."""
    return DeedSpec(
        doc_no="1188/2003", sro=SRO,
        execution_date="05-06-2003", registration_date="12-06-2003", registration_iso="2003-06-12",
        deed_type="Sale Deed", seller=GOVIND, buyer=RAMESH,
        survey_no=SURVEY_NO, plot_no=PLOT_NO, extent_sqyd=400.0, extent_text=EXTENT_400,
        boundaries=BOUNDARIES, locality=LOCALITY,
        consideration_inr=600000.0, consideration_text="Rs. 6,00,000/- (Rupees Six Lakhs only)",
        stamp_duty_text="Rs. 36,000/-", estamp_no="IN-TS41882003116742K",
        prior_deed_refs=(), prior_deed_date="", book_volume="Book-I, Volume 41, Pages 88-94",
    )


def _second_deed(buyer: PartySpec) -> DeedSpec:
    return DeedSpec(
        doc_no="2451/2011", sro=SRO,
        execution_date="02-09-2011", registration_date="05-09-2011", registration_iso="2011-09-05",
        deed_type="Sale Deed", seller=RAMESH, buyer=buyer,
        survey_no=SURVEY_NO, plot_no=PLOT_NO, extent_sqyd=400.0, extent_text=EXTENT_400,
        boundaries=BOUNDARIES, locality=LOCALITY,
        consideration_inr=4200000.0,
        consideration_text="Rs. 42,00,000/- (Rupees Forty Two Lakhs only)",
        stamp_duty_text="Rs. 2,52,000/-", estamp_no="IN-TS62445201193318L",
        prior_deed_refs=("1188/2003",), prior_deed_date="12-06-2003",
        book_volume="Book-I, Volume 87, Pages 210-216",
    )


def _third_deed(seller: PartySpec, extent_sqyd: float, extent_text: str) -> DeedSpec:
    return DeedSpec(
        doc_no="5820/2019", sro=SRO,
        execution_date="11-02-2019", registration_date="18-02-2019", registration_iso="2019-02-18",
        deed_type="Sale Deed", seller=seller, buyer=PRAKASH,
        survey_no=SURVEY_NO, plot_no=PLOT_NO, extent_sqyd=extent_sqyd, extent_text=extent_text,
        boundaries=BOUNDARIES, locality=LOCALITY,
        consideration_inr=9600000.0,
        consideration_text="Rs. 96,00,000/- (Rupees Ninety Six Lakhs only)",
        stamp_duty_text="Rs. 5,76,000/-", estamp_no="IN-TS80917201947725M",
        prior_deed_refs=("2451/2011",), prior_deed_date="05-09-2011",
        book_volume="Book-I, Volume 152, Pages 402-409",
    )


def build_bundles() -> tuple[BundleSpec, ...]:
    """Four bundles over the same parcel — one per link verdict the chain engine can return."""
    return (
        BundleSpec(
            filename="01_clean_chain.pdf",
            scenario=ScenarioKind.CLEAN.value,
            headline="Unbroken chain: every seller is the previous buyer, extents and recitals agree.",
            expected_overall=OVERALL_INTACT,
            expected_links=(LINK_LINKED, LINK_LINKED),
            deeds=(_root_deed(), _second_deed(SUNITA), _third_deed(SUNITA, 400.0, EXTENT_400)),
        ),
        BundleSpec(
            filename="02_weak_transliteration.pdf",
            scenario=ScenarioKind.WEAK.value,
            headline="Same chain, but the last seller's name is transliterated differently "
                     "('Lakshmi Narayanan' -> 'Laxmi Narayan') — a caveat for a human, not a break.",
            expected_overall=OVERALL_REVIEW,
            expected_links=(LINK_LINKED, LINK_WEAK),
            deeds=(_root_deed(), _second_deed(LAKSHMI),
                   _third_deed(LAKSHMI_VARIANT, 400.0, EXTENT_400)),
        ),
        BundleSpec(
            filename="03_gap_extent_overflow.pdf",
            scenario=ScenarioKind.GAP.value,
            headline="Sells more than she owns: bought 400 sq.yd in 2011, conveys 600 sq.yd in 2019 — "
                     "the extra 200 sq.yd has no source deed in the bundle.",
            expected_overall=OVERALL_REVIEW,
            expected_links=(LINK_LINKED, LINK_GAP),
            deeds=(_root_deed(), _second_deed(SUNITA), _third_deed(SUNITA, 600.0, EXTENT_600)),
        ),
        BundleSpec(
            filename="04_broken_stranger_seller.pdf",
            scenario=ScenarioKind.BROKEN.value,
            headline="A stranger sells: the 2019 vendor was never a buyer in this chain, yet his deed "
                     "cites 2451/2011 as his source of title.",
            expected_overall=OVERALL_BROKEN,
            expected_links=(LINK_LINKED, LINK_BROKEN),
            deeds=(_root_deed(), _second_deed(SUNITA), _third_deed(FAROOQ, 400.0, EXTENT_400)),
        ),
    )


# --------------------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------------------

def _write_readme(bundles: tuple[BundleSpec, ...], path: Path) -> None:
    lines = [
        "# Synthetic deed bundles",
        "",
        "Fabricated deeds over one imaginary parcel (Sy. No. 142/2, Plot 17, Kondapur), generated by",
        "`../make_samples.py`. Every name, document number and e-stamp number here is invented — these",
        "are test fixtures, not records of any real property or person.",
        "",
        "Each PDF bundles **3 sale deeds** (2 pages each, 6 pages total) into one file, the way a real",
        "link-document bundle arrives, so the upload exercises segmentation as well as chain logic.",
        "",
        "| File | Expected verdict | What it proves |",
        "|---|---|---|",
    ]
    for b in bundles:
        lines.append(f"| `{b.filename}` | **{b.expected_overall}** | {b.headline} |")
    lines += [
        "",
        "`single/` holds the same clean chain split across three one-deed files, for exercising the",
        "multi-file upload path instead of in-file segmentation.",
        "",
        "Expected verdicts are asserted against the real chain engine in `../test_samples.py`.",
        "",
        "> Extraction is a model call, so the *reported* verdict can differ if Gemini misreads a field.",
        "> That is the point: these fixtures separate an extraction failure from a chain-logic failure.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    fonts = _load_fonts()
    bundles = build_bundles()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for bundle in bundles:
        pages: list[Image.Image] = []
        for deed in bundle.deeds:
            pages.extend(_render_deed(deed, fonts))
        out = OUT_DIR / bundle.filename
        _save_pdf(pages, out)
        size_kb = out.stat().st_size / 1024
        print(f"  {out.name:<34} {len(pages)} pages  {size_kb:7.0f} KB   expect: {bundle.expected_overall}")

    clean = bundles[0]
    for idx, deed in enumerate(clean.deeds):
        out = OUT_DIR / "single" / f"deed_{chr(ord('A') + idx)}_{deed.doc_no.replace('/', '_')}.pdf"
        _save_pdf(_render_deed(deed, fonts), out)
        print(f"  single/{out.name:<27} 2 pages  {out.stat().st_size / 1024:7.0f} KB")

    _write_readme(bundles, OUT_DIR / "README.md")
    print(f"\nWrote {len(bundles)} bundles + 3 single-deed files to {OUT_DIR}")


if __name__ == "__main__":
    main()
