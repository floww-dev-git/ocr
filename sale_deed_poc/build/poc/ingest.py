"""Ingest — turn an uploaded file (PDF or image) into a list of PNG page images.

Single purpose: file bytes in, normalised page images out. Knows nothing about
extraction or the LLM.
"""
from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image

# Backstop only — a real bundle (deed + link documents) can run 80–120 pages, so this must be
# high enough to never silently drop link deeds. Configurable; a warning is surfaced if exceeded.
MAX_PAGES = int(os.environ.get("DEED_MAX_PAGES", "150"))
RENDER_SCALE = 2.0      # ~144 dpi; enough for OCR without huge payloads
INVENTORY_MAX_WIDTH = 1100   # inventory only detects document boundaries → low-res is fine + keeps payload small
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp"}


def _pil_to_png(img: Image.Image) -> bytes:
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def downscale_png(png: bytes, max_width: int = INVENTORY_MAX_WIDTH) -> bytes:
    """Shrink a page image (used for the all-pages inventory pass to keep the request small)."""
    with Image.open(BytesIO(png)) as img:
        if img.width <= max_width:
            return png
        h = round(img.height * max_width / img.width)
        return _pil_to_png(img.resize((max_width, h)))


def page_count(path: str | Path) -> int:
    """How many pages the source actually has (before any cap) — so callers can warn on truncation."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        pdf = pdfium.PdfDocument(str(path))
        try:
            return len(pdf)
        finally:
            pdf.close()
    return 1


def file_to_page_pngs(path: str | Path) -> list[bytes]:
    """Return PNG bytes per page. PDFs are rendered; images pass through (normalised)."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        pages: list[bytes] = []
        pdf = pdfium.PdfDocument(str(path))
        try:
            n = min(len(pdf), MAX_PAGES)
            for i in range(n):
                bitmap = pdf[i].render(scale=RENDER_SCALE)
                pages.append(_pil_to_png(bitmap.to_pil()))
        finally:
            pdf.close()
        return pages

    if suffix in IMAGE_EXTS:
        with Image.open(path) as img:
            return [_pil_to_png(img)]

    raise ValueError(f"Unsupported file type: {suffix} ({path.name})")
