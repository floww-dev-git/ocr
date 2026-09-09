"""Generate the shipped deed bundles as real PDFs, so the upload path has real paper.

A real title bundle is private, so these are fabricated: one PDF per engineered
history, each holding three registered deeds back to back over one imaginary parcel.
Every deed opens with a fresh e-stamp header and a 'SALE DEED' title, which is the
boundary cue the inventory pass segments on.

    cd backend && uv run python scripts/make_deed_bundles.py

The deeds are read from document_extraction's own bundle specs, so the paper and the
canned offline read can never drift apart: change the spec and the PDF follows.

Ported from sale_deed_poc/build/poc/make_samples.py. Two deliberate departures from
it, both so a real read of this paper agrees with the canned one: the village is
printed on its own line rather than folded into a locality string, and the boundary
schedule is split back into its four clauses.
"""
import os
import sys
from pathlib import Path
from typing import Dict, List

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from document_extraction.adapters.bundle_sample_reads import (  # noqa: E402
    BOUNDARY_SIDES,
    BUNDLE_SPECS,
    DISTRICT,
    MANDAL,
    BundleSpec,
)
from document_extraction.adapters.deed_sample_reads import DeedSampleSpec  # noqa: E402

OUTPUT_DIRECTORY = BACKEND_ROOT / "samples"

PAGE_WIDTH, PAGE_HEIGHT = 1240, 1754  # A4 at 150 dpi
MARGIN = 96
BODY_WIDTH = PAGE_WIDTH - 2 * MARGIN
RESOLUTION = 150.0

FONT_DIRECTORY = Path("/usr/share/fonts/truetype/dejavu")
FONT_FILES = {
    "body": ("DejaVuSerif.ttf", 23),
    "body_bold": ("DejaVuSerif-Bold.ttf", 23),
    "small": ("DejaVuSerif.ttf", 19),
    "title": ("DejaVuSans-Bold.ttf", 44),
    "sub": ("DejaVuSans-Bold.ttf", 26),
    "mono": ("DejaVuSansMono.ttf", 21),
}

INK = 25  # near-black on white, like a clean scan
GREY = 90
LABEL_COLUMN = 300

WITNESSES = (
    "1.  K. Srinivasa Rao, s/o K. Ramulu, Kondapur, Hyderabad",
    "2.  M. Anitha, w/o M. Suresh, Gachibowli, Hyderabad",
)
BOOK_VOLUME_BY_DOCUMENT_NUMBER = {
    "1188/2003": "Book-I, Volume 41, Pages 88-94",
    "2451/2011": "Book-I, Volume 87, Pages 210-216",
    "5820/2019": "Book-I, Volume 152, Pages 402-409",
}
ROOT_RECITAL = (
    "WHEREAS the Vendor is the sole and absolute owner and in peaceful possession of "
    "the property more fully described in the Schedule hereunder, the same having "
    "been assigned to the Vendor by the District Collector, Ranga Reddy District, "
    "under Assignment Patta No. 118/1987 dated 14-08-1987, and the Vendor's name "
    "having been duly mutated in the revenue records thereafter."
)


class SampleGenerationError(RuntimeError):
    """Raised when a bundle cannot be rendered: missing fonts, unwritable output."""


class PageWriter:
    """A cursor over one page image, drawing top-down."""

    def __init__(self, fonts: Dict[str, ImageFont.FreeTypeFont]) -> None:
        self.image = Image.new("L", (PAGE_WIDTH, PAGE_HEIGHT), color=255)
        self.draw = ImageDraw.Draw(self.image)
        self.fonts = fonts
        self.y = MARGIN

    def gap(self, pixels: int) -> None:
        self.y += pixels

    def rule(self) -> None:
        self.draw.line(
            [(MARGIN, self.y), (PAGE_WIDTH - MARGIN, self.y)], fill=GREY, width=2
        )
        self.y += 18

    def centered(self, text: str, font_key: str, fill: int = INK) -> None:
        font = self.fonts[font_key]
        width = self.draw.textlength(text, font=font)
        self.draw.text(((PAGE_WIDTH - width) / 2, self.y), text, font=font, fill=fill)
        self.y += font.size + 12

    def para(
        self, text: str, font_key: str = "body", indent: int = 0, fill: int = INK
    ) -> None:
        font = self.fonts[font_key]
        for line in self._wrap(text=text, font=font, width=BODY_WIDTH - indent):
            self.draw.text((MARGIN + indent, self.y), line, font=font, fill=fill)
            self.y += font.size + 10

    def columns(self, left: str, right: str, font_key: str = "body") -> None:
        """Two real columns. Padding with spaces cannot work in a proportional font,
        and a collapsed signature block reads as one long name to the extractor."""
        font = self.fonts[font_key]
        self.draw.text((MARGIN, self.y), left, font=font, fill=INK)
        self.draw.text((MARGIN + BODY_WIDTH // 2, self.y), right, font=font, fill=INK)
        self.y += font.size + 10

    def key_value(self, label: str, value: str, font_key: str = "body") -> None:
        font = self.fonts[font_key]
        self.draw.text((MARGIN, self.y), label, font=self.fonts["body_bold"], fill=INK)
        self.draw.text(
            (MARGIN + LABEL_COLUMN, self.y), value, font=font, fill=INK
        )
        self.y += font.size + 10

    def _wrap(
        self, text: str, font: ImageFont.FreeTypeFont, width: int
    ) -> List[str]:
        lines: List[str] = []
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


def load_fonts() -> Dict[str, ImageFont.FreeTypeFont]:
    missing = sorted(
        {
            filename
            for filename, _ in FONT_FILES.values()
            if not (FONT_DIRECTORY / filename).exists()
        }
    )
    if missing:
        raise SampleGenerationError(
            f"Missing DejaVu fonts {missing} in {FONT_DIRECTORY}. Install them with: "
            f"sudo apt-get install fonts-dejavu-core"
        )
    return {
        key: ImageFont.truetype(str(FONT_DIRECTORY / filename), size)
        for key, (filename, size) in FONT_FILES.items()
    }


def format_date(iso_date: str) -> str:
    """As a deed prints it: dd-mm-yyyy. Extraction is what normalises it back."""
    year, month, day = iso_date.split("-")
    return f"{day}-{month}-{year}"


def describe_party(name: str, relation: str, relative_name: str, address: str) -> str:
    return f"{name}, {relation} {relative_name}, residing at {address}"


def render_deed(
    deed: DeedSampleSpec, fonts: Dict[str, ImageFont.FreeTypeFont]
) -> List[Image.Image]:
    """One deed onto two pages: the parties and recital, then the Schedule."""
    return [
        _render_first_page(deed=deed, fonts=fonts),
        _render_second_page(deed=deed, fonts=fonts),
    ]


def _render_first_page(
    deed: DeedSampleSpec, fonts: Dict[str, ImageFont.FreeTypeFont]
) -> Image.Image:
    page = PageWriter(fonts)
    execution_date = format_date(deed.execution_date or deed.registration_date)
    page.centered("INDIA NON JUDICIAL", "sub", fill=GREY)
    page.centered("GOVERNMENT OF TELANGANA", "sub", fill=GREY)
    page.gap(6)
    page.para(f"e-Stamp Certificate No. : {deed.estamp_no}", font_key="mono")
    page.para(f"Stamp Duty Paid         : {deed.stamp_duty_text}", font_key="mono")
    page.gap(14)
    page.rule()
    page.centered("SALE DEED", "title")
    page.rule()
    page.gap(10)
    page.key_value("Document No.", deed.doc_no)
    page.key_value("Sub-Registrar Office", deed.sro)
    page.key_value("Date of Execution", execution_date)
    page.key_value("Date of Registration", format_date(deed.registration_date))
    page.gap(20)
    page.para(f"This Sale Deed is made and executed on this {execution_date} BETWEEN:")
    page.gap(14)
    _render_party(page=page, role="VENDOR", party=deed.vendor_party, name=deed.vendor)
    page.gap(10)
    page.para("AND", font_key="body_bold")
    page.gap(10)
    _render_party(
        page=page, role="VENDEE", party=deed.purchaser_party, name=deed.purchaser
    )
    page.gap(24)
    page.para(_recital(deed))
    page.gap(18)
    page.para(
        f"AND WHEREAS the Vendee has offered to purchase the said property for a "
        f"total consideration of {deed.consideration_text}, which the Vendor has "
        f"agreed to accept."
    )
    page.gap(18)
    page.para(
        f"NOW THIS DEED WITNESSETH that in consideration of the sum of "
        f"{deed.consideration_text} paid by the Vendee to the Vendor, the receipt of "
        f"which the Vendor hereby acknowledges, the Vendor doth hereby grant, convey, "
        f"transfer and assure unto the Vendee the property described in the Schedule "
        f"hereunder, TO HAVE AND TO HOLD the same absolutely and forever, free from "
        f"all encumbrances, charges, liens, attachments and court proceedings."
    )
    return page.image


def _render_party(page: PageWriter, role: str, party, name: str) -> None:
    page.para(f"{role}:", font_key="body_bold")
    described = (
        describe_party(
            name=party.name,
            relation=party.relation or "",
            relative_name=party.relative_name or "",
            address=party.address or "",
        )
        if party is not None
        else name
    )
    page.para(described, indent=40)
    page.para(
        f"(hereinafter called the {role}, which expression shall include their "
        f"heirs, executors, administrators and assigns)",
        indent=40,
        font_key="small",
    )


def _recital(deed: DeedSampleSpec) -> str:
    if not deed.prior_deed_refs:
        return ROOT_RECITAL
    return (
        f"WHEREAS the Vendor is the sole and absolute owner and in peaceful "
        f"possession of the property more fully described in the Schedule hereunder, "
        f"having acquired the same under and by virtue of registered Sale Deed "
        f"bearing Document No. {', '.join(deed.prior_deed_refs)} of the "
        f"Sub-Registrar Office, {deed.sro}."
    )


def _render_second_page(
    deed: DeedSampleSpec, fonts: Dict[str, ImageFont.FreeTypeFont]
) -> Image.Image:
    page = PageWriter(fonts)
    page.centered("SCHEDULE OF PROPERTY", "sub")
    page.rule()
    page.gap(10)
    page.key_value("Survey No.", deed.survey_no)
    page.key_value("Plot No.", deed.plot_no)
    page.key_value("Extent", deed.extent_text)
    # Printed on its own line, so a read of this paper reports the village the
    # application names rather than a whole postal hierarchy.
    page.key_value("Village", deed.village)
    page.key_value("Mandal / District", f"{MANDAL} Mandal, {DISTRICT} District")
    page.gap(16)
    page.para("Bounded by:", font_key="body_bold")
    for side, description in BOUNDARY_SIDES:
        page.para(f"{side:<6}:  {description}", indent=40, font_key="mono")
    page.gap(28)
    page.para(
        "IN WITNESS WHEREOF the Vendor and the Vendee have set their hands to this "
        "deed on the day, month and year first above written, in the presence of the "
        "witnesses below."
    )
    page.gap(30)
    page.para("WITNESSES:", font_key="body_bold")
    for witness in WITNESSES:
        page.para(witness, indent=40)
    page.gap(40)
    page.columns("(Signature)", "(Signature)", font_key="small")
    page.columns(deed.vendor, deed.purchaser, font_key="body_bold")
    page.columns("VENDOR", "VENDEE", font_key="small")
    page.gap(36)
    page.rule()
    page.centered("REGISTRATION ENDORSEMENT", "sub")
    page.gap(6)
    page.para(
        f"Registered as Document No. {deed.doc_no}, "
        f"{BOOK_VOLUME_BY_DOCUMENT_NUMBER.get(deed.doc_no, 'Book-I')}, in the office "
        f"of the Sub-Registrar, {deed.sro}, {DISTRICT} District, on "
        f"{format_date(deed.registration_date)}.",
        font_key="small",
    )
    page.gap(10)
    page.para("Sd/- SUB-REGISTRAR", font_key="body_bold")
    page.para(deed.sro, font_key="small")
    return page.image


def save_pdf(pages: List[Image.Image], path: Path) -> None:
    if not pages:
        raise SampleGenerationError(
            f"Refusing to write {path.name}: no pages were rendered."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        path, "PDF", save_all=True, append_images=pages[1:], resolution=RESOLUTION
    )


def render_bundle(
    bundle: BundleSpec, fonts: Dict[str, ImageFont.FreeTypeFont]
) -> List[Image.Image]:
    pages: List[Image.Image] = []
    for deed in bundle.deeds:
        pages.extend(render_deed(deed=deed, fonts=fonts))
    return pages


def main() -> None:
    fonts = load_fonts()
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for bundle in BUNDLE_SPECS:
        pages = render_bundle(bundle=bundle, fonts=fonts)
        output_path = OUTPUT_DIRECTORY / bundle.filename
        save_pdf(pages=pages, path=output_path)
        size_kb = output_path.stat().st_size / 1024
        print(
            f"  {output_path.name:<34} {len(pages)} pages  {size_kb:7.0f} KB  "
            f"{bundle.headline[:52]}"
        )
    print(f"\nWrote {len(BUNDLE_SPECS)} bundles to {OUTPUT_DIRECTORY}")


if __name__ == "__main__":
    main()
