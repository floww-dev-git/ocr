from io import BytesIO
from pathlib import Path
from typing import List, Tuple

import pypdfium2 as pdfium
from django.conf import settings
from PIL import Image

from document_extraction.exceptions.extraction_exceptions import ExtractionFailed

RENDER_SCALE = 2.0
CLASSIFICATION_MAX_WIDTH = 1100
PDF_SUFFIX = ".pdf"
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".bmp")


def _to_png_bytes(image: Image.Image) -> bytes:
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def downscale_png(png: bytes, max_width: int = CLASSIFICATION_MAX_WIDTH) -> bytes:
    with Image.open(BytesIO(png)) as image:
        if image.width <= max_width:
            return png
        height = round(image.height * max_width / image.width)
        return _to_png_bytes(image.resize((max_width, height)))


def render_page_images(file_path: str) -> Tuple[List[bytes], int]:
    path = Path(file_path)
    if not path.is_file():
        raise ExtractionFailed(filename=path.name, reason="The stored file is missing.")

    suffix = path.suffix.lower()
    if suffix == PDF_SUFFIX:
        return _render_pdf_pages(path)
    if suffix in IMAGE_SUFFIXES:
        with Image.open(path) as image:
            return [_to_png_bytes(image)], 1
    raise ExtractionFailed(
        filename=path.name, reason=f"{suffix} is not a readable document format."
    )


def _render_pdf_pages(path: Path) -> Tuple[List[bytes], int]:
    pages: List[bytes] = []
    pdf = pdfium.PdfDocument(str(path))
    try:
        total_page_count = len(pdf)
        rendered_count = min(total_page_count, settings.MAX_DOCUMENT_PAGES)
        for page_index in range(rendered_count):
            bitmap = pdf[page_index].render(scale=RENDER_SCALE)
            pages.append(_to_png_bytes(bitmap.to_pil()))
    finally:
        pdf.close()
    return pages, total_page_count
