"""Generate synthetic Aadhaar SPECIMEN documents for the capability showcase.

A real Aadhaar is private and carries live PII, so these are fabricated specimens,
each engineered to exercise one Aadhaar verification capability against the single
showcase application (BN/2026/0601). Every page is watermarked
"SPECIMEN - NOT A REAL AADHAAR".

    cd backend && uv run python scripts/generate_aadhaar_specimens.py

Each specimen is a two-page PDF (front + reverse). The reverse carries a REAL,
decodable QR generated with segno, encoding a payload WE control — a simple
delimited text, deliberately NOT the encrypted/signed secure-QR a production
Aadhaar uses. The QR-vs-print integrity check reads this payload back and compares
it to what the model OCRs off the front, which is a genuine check for these
specimens (see ADR-013 for the honest boundary).

The three first-slice specimens:
  - aadhaar_clean.pdf         Verhoeff-valid number, QR agrees with the print.
  - aadhaar_tampered_qr.pdf   printed name/number edited; QR still carries the clean
                              identity, so QR and print disagree (the tamper signal).
  - aadhaar_invalid_number.pdf  a twelve-digit, valid-leading-digit number that FAILS
                              the Verhoeff checksum; QR agrees with the (invalid) print.

Second-slice specimens:
  - aadhaar_mismatch.pdf      a clean card for a DIFFERENT person than the application.
  - aadhaar_poor_scan.pdf     the clean card, blurred/skewed/downscaled.

The numbers here are computed to pass or fail Verhoeff on purpose; they are not real
Aadhaar numbers.
"""
import io
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import segno
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# The Verhoeff helper is the same one the checksum check uses, so the numbers this
# script bakes in are valid or invalid by exactly the rule the check enforces.
from document_scrutiny.domain.aadhaar_verhoeff import (  # noqa: E402
    append_verhoeff_check_digit,
    is_verhoeff_valid,
)

OUTPUT_DIRECTORY = BACKEND_ROOT / "samples" / "aadhaar"

PAGE_WIDTH, PAGE_HEIGHT = 1000, 640  # a card-proportioned page at ~150 dpi
MARGIN = 40
INK = 20
GREY = 110
SAFFRON = (255, 153, 51)
GREEN = (19, 136, 8)
UIDAI_RED = (196, 62, 48)

FONT_DIRECTORY = Path("/usr/share/fonts/truetype/dejavu")
FONT_FILES = {
    "title": ("DejaVuSans-Bold.ttf", 30),
    "sub": ("DejaVuSans-Bold.ttf", 20),
    "label": ("DejaVuSans.ttf", 18),
    "value": ("DejaVuSans-Bold.ttf", 22),
    "uid": ("DejaVuSansMono-Bold.ttf", 40),
    "small": ("DejaVuSans.ttf", 15),
    "watermark": ("DejaVuSans-Bold.ttf", 34),
}


class SpecimenError(RuntimeError):
    """Raised when a specimen cannot be rendered: missing fonts, unwritable output."""


@dataclass(frozen=True)
class AadhaarSpecimen:
    slug: str
    # What is PRINTED on the card front.
    printed_name: str
    printed_number: str
    dob: str
    gender: str
    address: str
    # What the QR payload carries. When this differs from the printed values, the
    # QR-vs-print check catches it. None means "same as printed".
    qr_name: Optional[str] = None
    qr_number: Optional[str] = None
    qr_dob: Optional[str] = None
    degrade: bool = False  # blur/skew/downscale for the poor-scan specimen

    def qr_payload(self) -> str:
        name = self.qr_name if self.qr_name is not None else self.printed_name
        number = self.qr_number if self.qr_number is not None else self.printed_number
        dob = self.qr_dob if self.qr_dob is not None else self.dob
        # A documented, plain-text payload we control — not real secure-QR.
        return f"AADHAAR|name={name}|uid={number}|dob={dob}|gender={self.gender}"


# The showcase applicant, matching application BN/2026/0601. A Verhoeff-valid number
# is built from an 11-digit stem (leading digit 2, never 0/1) plus a check digit.
_CLEAN_NAME = "Rithika Sharma"
_CLEAN_STEM = "23456789012"
_CLEAN_NUMBER = append_verhoeff_check_digit(_CLEAN_STEM)  # 12 digits, checksum-valid
_CLEAN_DOB = "1990-06-15"
_CLEAN_GENDER = "Female"
_CLEAN_ADDRESS = (
    "Flat 5B, Lake View Residency, Kondapur, Serilingampally, "
    "Ranga Reddy, Telangana 500084"
)

# An invalid number: same stem, but a check digit that is deliberately wrong, so it
# is twelve digits with a valid leading digit yet fails Verhoeff.
_INVALID_NUMBER = _CLEAN_STEM + str((int(_CLEAN_NUMBER[-1]) + 1) % 10)

# A different person, for the mismatch specimen.
_OTHER_NAME = "Vikram Anand Reddy"
_OTHER_STEM = "56789012345"
_OTHER_NUMBER = append_verhoeff_check_digit(_OTHER_STEM)
_OTHER_DOB = "1985-02-09"

# The tampered card: the print is altered to a different name and number, but the QR
# still carries the clean identity — so QR and print contradict each other.
_TAMPERED_PRINTED_NAME = "Rithika Verma"
_TAMPERED_PRINTED_NUMBER = append_verhoeff_check_digit("98765432101")

SPECIMENS: List[AadhaarSpecimen] = [
    AadhaarSpecimen(
        slug="aadhaar_clean",
        printed_name=_CLEAN_NAME,
        printed_number=_CLEAN_NUMBER,
        dob=_CLEAN_DOB,
        gender=_CLEAN_GENDER,
        address=_CLEAN_ADDRESS,
    ),
    AadhaarSpecimen(
        slug="aadhaar_tampered_qr",
        printed_name=_TAMPERED_PRINTED_NAME,
        printed_number=_TAMPERED_PRINTED_NUMBER,
        dob=_CLEAN_DOB,
        gender=_CLEAN_GENDER,
        address=_CLEAN_ADDRESS,
        # QR keeps the original clean identity.
        qr_name=_CLEAN_NAME,
        qr_number=_CLEAN_NUMBER,
        qr_dob=_CLEAN_DOB,
    ),
    AadhaarSpecimen(
        slug="aadhaar_invalid_number",
        printed_name=_CLEAN_NAME,
        printed_number=_INVALID_NUMBER,
        dob=_CLEAN_DOB,
        gender=_CLEAN_GENDER,
        address=_CLEAN_ADDRESS,
    ),
    AadhaarSpecimen(
        slug="aadhaar_mismatch",
        printed_name=_OTHER_NAME,
        printed_number=_OTHER_NUMBER,
        dob=_OTHER_DOB,
        gender="Male",
        address=(
            "H.No 8-2-120, Banjara Hills, Road No 3, Hyderabad, Telangana 500034"
        ),
    ),
    AadhaarSpecimen(
        slug="aadhaar_poor_scan",
        printed_name=_CLEAN_NAME,
        printed_number=_CLEAN_NUMBER,
        dob=_CLEAN_DOB,
        gender=_CLEAN_GENDER,
        address=_CLEAN_ADDRESS,
        degrade=True,
    ),
    AadhaarSpecimen(
        # A near-match, not a wrong person: the printed name drops one letter
        # ('Ritika' for 'Rithika'), the kind of slip an OCR read or a data-entry
        # clerk makes. The QR still carries the correct spelling. Everything else is
        # the clean identity, so the only thing off is the printed name — and it is
        # close enough that the department and the QR treat it as the same person,
        # while the check against the declared application flags it for a look.
        slug="aadhaar_name_typo",
        printed_name="Ritika Sharma",
        printed_number=_CLEAN_NUMBER,
        dob=_CLEAN_DOB,
        gender=_CLEAN_GENDER,
        address=_CLEAN_ADDRESS,
        qr_name=_CLEAN_NAME,
        qr_number=_CLEAN_NUMBER,
        qr_dob=_CLEAN_DOB,
    ),
    AadhaarSpecimen(
        # Internally inconsistent on its own terms: the printed date of birth is in
        # the future, which no genuine document could carry. The intrinsic check
        # catches it from the document alone, before any comparison. Everything else
        # is the clean identity; the QR carries the same (impossible) date so the QR
        # agrees with the print — this is a bad document, not a tampered one.
        slug="aadhaar_impossible_dob",
        printed_name=_CLEAN_NAME,
        printed_number=_CLEAN_NUMBER,
        dob="2035-01-02",
        gender=_CLEAN_GENDER,
        address=_CLEAN_ADDRESS,
        qr_name=_CLEAN_NAME,
        qr_number=_CLEAN_NUMBER,
        qr_dob="2035-01-02",
    ),
]


@dataclass(frozen=True)
class PanSpecimen:
    """The applicant's own PAN, for the cross-document reconciliation scenario.

    On its own it agrees with the application. Its reason for existing is to be
    filed alongside the wrong-person Aadhaar: the two identity documents then name
    different people, which the cross-document check surfaces. Rendered here so the
    demo can drag in a real second document rather than a placeholder.
    """

    slug: str
    name: str
    parent_name: str
    dob: str
    pan: str


# The showcase applicant's PAN — same person as the clean Aadhaar and the
# application (BN/2026/0601). PAN prints the name in uppercase.
PAN_SPECIMEN = PanSpecimen(
    slug="pan_rithika",
    name="RITHIKA SHARMA",
    parent_name="ANIL KUMAR SHARMA",
    dob=_CLEAN_DOB,
    pan="AKRPS4416H",
)


def load_fonts() -> dict:
    if not FONT_DIRECTORY.is_dir():
        raise SpecimenError(f"Font directory not found: {FONT_DIRECTORY}")
    fonts = {}
    for name, (filename, size) in FONT_FILES.items():
        path = FONT_DIRECTORY / filename
        if not path.is_file():
            raise SpecimenError(f"Missing font {filename} in {FONT_DIRECTORY}")
        fonts[name] = ImageFont.truetype(str(path), size)
    return fonts


def _format_uid(number: str) -> str:
    return f"{number[0:4]} {number[4:8]} {number[8:12]}"


def _watermark(image: Image.Image, fonts: dict) -> None:
    draw = ImageDraw.Draw(image)
    text = "SPECIMEN - NOT A REAL AADHAAR"
    for row in range(-1, PAGE_HEIGHT // 120 + 2):
        y = row * 120 + 20
        draw.text((60, y), text, font=fonts["watermark"], fill=(210, 210, 210))


def _render_front(specimen: AadhaarSpecimen, fonts: dict) -> Image.Image:
    image = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
    _watermark(image, fonts)
    draw = ImageDraw.Draw(image)

    # Tricolour band + government line, like the UIDAI header.
    draw.rectangle([0, 0, PAGE_WIDTH, 12], fill=SAFFRON)
    draw.rectangle([0, PAGE_HEIGHT - 12, PAGE_WIDTH, PAGE_HEIGHT], fill=GREEN)
    draw.ellipse([MARGIN, 40, MARGIN + 70, 110], outline=UIDAI_RED, width=3)
    draw.text((MARGIN + 90, 44), "भारत सरकार", font=fonts["sub"], fill=INK)
    draw.text((MARGIN + 90, 74), "Government of India", font=fonts["sub"], fill=INK)
    draw.text(
        (PAGE_WIDTH - 260, 54),
        "Unique Identification\nAuthority of India",
        font=fonts["small"],
        fill=GREY,
    )

    # Photograph box (a plain framed rectangle stands in for the portrait).
    photo_box = [MARGIN, 170, MARGIN + 190, 430]
    draw.rectangle(photo_box, outline=GREY, width=2)
    draw.text((MARGIN + 40, 285), "PHOTO", font=fonts["label"], fill=GREY)

    detail_x = MARGIN + 230
    y = 180
    for label, value in (
        ("Name", specimen.printed_name),
        ("DOB", specimen.dob),
        ("Gender", specimen.gender),
    ):
        draw.text((detail_x, y), label, font=fonts["label"], fill=GREY)
        draw.text((detail_x, y + 24), value, font=fonts["value"], fill=INK)
        y += 78

    # The Aadhaar number, in the spaced triple-group form.
    draw.text(
        (detail_x, 470), _format_uid(specimen.printed_number), font=fonts["uid"], fill=INK
    )
    return image


def _render_back(specimen: AadhaarSpecimen, fonts: dict) -> Image.Image:
    image = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
    _watermark(image, fonts)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, PAGE_WIDTH, 12], fill=SAFFRON)
    draw.rectangle([0, PAGE_HEIGHT - 12, PAGE_WIDTH, PAGE_HEIGHT], fill=GREEN)

    draw.text((MARGIN, 60), "Address", font=fonts["label"], fill=GREY)
    _wrap(draw, specimen.address, fonts["value"], MARGIN, 90, PAGE_WIDTH - 360, 30)

    # The QR, generated real and decodable, placed top-right like a real card.
    qr = segno.make(specimen.qr_payload(), error="m")
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=7, border=3)
    buffer.seek(0)
    qr_image = Image.open(buffer).convert("RGB")
    image.paste(qr_image, (PAGE_WIDTH - qr_image.width - MARGIN, 50))

    draw.text(
        (MARGIN, PAGE_HEIGHT - 60),
        _format_uid(specimen.printed_number),
        font=fonts["uid"],
        fill=INK,
    )
    return image


def _wrap(draw, text, font, x, y, max_width, line_height) -> None:
    words = text.split()
    line = ""
    for word in words:
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) > max_width and line:
            draw.text((x, y), line, font=font, fill=INK)
            y += line_height
            line = word
        else:
            line = trial
    if line:
        draw.text((x, y), line, font=font, fill=INK)


def _degrade(image: Image.Image) -> Image.Image:
    """A poor scan: downscale, blur, and a slight skew, then back up to size."""
    small = image.resize((PAGE_WIDTH // 2, PAGE_HEIGHT // 2), Image.BILINEAR)
    blurred = small.filter(ImageFilter.GaussianBlur(radius=1.4))
    skewed = blurred.rotate(2.0, resample=Image.BICUBIC, fillcolor="white", expand=False)
    return skewed.resize((PAGE_WIDTH, PAGE_HEIGHT), Image.BILINEAR)


def render_specimen(specimen: AadhaarSpecimen, fonts: dict) -> List[Image.Image]:
    pages = [_render_front(specimen, fonts), _render_back(specimen, fonts)]
    if specimen.degrade:
        pages = [_degrade(page) for page in pages]
    return pages


def _pan_watermark(image: Image.Image, fonts: dict) -> None:
    draw = ImageDraw.Draw(image)
    text = "SPECIMEN - NOT A REAL PAN"
    for row in range(-1, PAGE_HEIGHT // 120 + 2):
        y = row * 120 + 20
        draw.text((60, y), text, font=fonts["watermark"], fill=(210, 210, 210))


def render_pan_specimen(specimen: PanSpecimen, fonts: dict) -> List[Image.Image]:
    """A single-page PAN card standing in for the applicant's own PAN.

    A plain, honest specimen — enough for a reviewer to read a name, a date of
    birth and the PAN off it, so the cross-document scenario has a real second
    document to reconcile against.
    """
    image = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), "white")
    _pan_watermark(image, fonts)
    draw = ImageDraw.Draw(image)

    income_tax_blue = (28, 63, 122)
    draw.rectangle([0, 0, PAGE_WIDTH, 12], fill=income_tax_blue)
    draw.rectangle([0, PAGE_HEIGHT - 12, PAGE_WIDTH, PAGE_HEIGHT], fill=income_tax_blue)
    draw.ellipse([MARGIN, 40, MARGIN + 70, 110], outline=income_tax_blue, width=3)
    draw.text((MARGIN + 90, 44), "आयकर विभाग", font=fonts["sub"], fill=INK)
    draw.text((MARGIN + 90, 74), "INCOME TAX DEPARTMENT", font=fonts["sub"], fill=INK)
    draw.text((PAGE_WIDTH - 260, 54), "GOVT. OF INDIA", font=fonts["small"], fill=GREY)

    # Photo and signature boxes, like a real card.
    draw.rectangle([MARGIN, 380, MARGIN + 170, 590], outline=GREY, width=2)
    draw.text((MARGIN + 40, 475), "PHOTO", font=fonts["label"], fill=GREY)
    draw.rectangle([PAGE_WIDTH - 250, 520, PAGE_WIDTH - MARGIN, 590], outline=GREY, width=2)
    draw.text((PAGE_WIDTH - 235, 545), "signature", font=fonts["small"], fill=GREY)

    detail_x = MARGIN + 230
    y = 180
    for label, value in (
        ("Name", specimen.name),
        ("Father's Name", specimen.parent_name),
        ("Date of Birth", specimen.dob),
    ):
        draw.text((detail_x, y), label, font=fonts["label"], fill=GREY)
        draw.text((detail_x, y + 24), value, font=fonts["value"], fill=INK)
        y += 78

    # The PAN itself, in the card's characteristic large mono type.
    draw.text((MARGIN, 300), "Permanent Account Number", font=fonts["label"], fill=GREY)
    draw.text((MARGIN, 324), specimen.pan, font=fonts["uid"], fill=INK)
    return [image]


def write_pdf(pages: List[Image.Image], path: Path) -> None:
    first, rest = pages[0], pages[1:]
    first.save(path, "PDF", resolution=150.0, save_all=True, append_images=rest)


def main() -> None:
    fonts = load_fonts()
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for specimen in SPECIMENS:
        pages = render_specimen(specimen, fonts)
        path = OUTPUT_DIRECTORY / f"{specimen.slug}.pdf"
        write_pdf(pages, path)
        checksum = "valid" if is_verhoeff_valid(specimen.printed_number) else "INVALID"
        print(f"wrote {path.name}  (printed number {checksum})")

    # The applicant's PAN, the second document in the cross-document scenario.
    pan_pages = render_pan_specimen(PAN_SPECIMEN, fonts)
    pan_path = OUTPUT_DIRECTORY / f"{PAN_SPECIMEN.slug}.pdf"
    write_pdf(pan_pages, pan_path)
    print(f"wrote {pan_path.name}  (PAN {PAN_SPECIMEN.pan})")

    print(f"\nSpecimens written to {OUTPUT_DIRECTORY}")


if __name__ == "__main__":
    main()
