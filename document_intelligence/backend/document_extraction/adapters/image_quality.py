"""A heuristic legibility score for a scanned document page.

Honest about being a heuristic: it does not judge whether a document is genuine,
only whether the scan is clear enough to rely on what was read from it. The signal
is the variance of the Laplacian — a standard, cheap sharpness measure: a crisp scan
has high edge variance, a blurred one low. Combined with the page resolution, it
gives a 0..1 score the quality check turns into a "verify against the original"
warning when it falls below the floor.
"""
from io import BytesIO
from typing import List, Optional

import numpy as np
from PIL import Image

from document_extraction.dtos.document_record_dtos import DocumentQualityDTO

# A sharp scan of printed text sits well above this Laplacian variance; a soft or
# downscaled photo falls far below it. Calibrated against the specimen generator's
# deliberate blur (a clean card scores ~800, the degraded one ~9), and kept generous
# so an ordinary phone photo is not flagged. Blur is the governing signal.
_BLUR_FLOOR = 120.0
# A secondary floor: below this shorter-edge pixel count even a sharp scan is too
# small to trust. Set for card-sized documents, which render smaller than an A4 page.
_MIN_RESOLUTION_PX = 400


def _laplacian_variance(gray: np.ndarray) -> float:
    # A 3x3 Laplacian kernel convolved by hand (no OpenCV dependency needed here),
    # then the variance of the response.
    kernel = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    padded = np.pad(gray.astype(np.float64), 1, mode="edge")
    response = (
        kernel[0, 1] * padded[:-2, 1:-1]
        + kernel[1, 0] * padded[1:-1, :-2]
        + kernel[1, 1] * padded[1:-1, 1:-1]
        + kernel[1, 2] * padded[1:-1, 2:]
        + kernel[2, 1] * padded[2:, 1:-1]
    )
    return float(response.var())


def _assess_one(png: bytes) -> DocumentQualityDTO:
    with Image.open(BytesIO(png)) as image:
        gray = np.array(image.convert("L"))
    shorter_edge = int(min(gray.shape[:2]))
    blur_score = _laplacian_variance(gray)
    blur_ratio = min(1.0, blur_score / _BLUR_FLOOR)
    resolution_ratio = min(1.0, shorter_edge / _MIN_RESOLUTION_PX)
    score = round(blur_ratio * resolution_ratio, 2)
    legible = blur_score >= _BLUR_FLOOR and shorter_edge >= _MIN_RESOLUTION_PX
    return DocumentQualityDTO(
        score=score,
        blur_score=round(blur_score, 1),
        resolution_px=shorter_edge,
        legible=legible,
    )


def assess_quality(page_images: List[bytes]) -> Optional[DocumentQualityDTO]:
    """The weakest page's quality, or None if nothing could be assessed.

    The worst page governs: one clear page does not make an illegible one readable.
    """
    assessments = []
    for png in page_images:
        try:
            assessments.append(_assess_one(png))
        except Exception:
            continue
    if not assessments:
        return None
    return min(assessments, key=lambda quality: quality.score)
