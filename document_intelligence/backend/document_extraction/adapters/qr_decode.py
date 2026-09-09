"""Decode a QR carried on a document page, and parse the payload we control.

Used to read the QR printed on an Aadhaar specimen so the scrutiny engine can
compare what the QR carries against what the model read off the print — a genuine
integrity check for our specimens (see ADR-013). The decoder is OpenCV's, which
needs no system package; a QR that fills only a corner of the page is found by
detecting its box first, then decoding an upscaled crop.

Honest boundary: this reads the plain-text payload our specimen generator embeds
(`AADHAAR|name=..|uid=..|dob=..|gender=..`). A production Aadhaar carries an
encrypted, signed secure-QR this does not attempt to decode.
"""
from io import BytesIO
from typing import Dict, List, Optional

import numpy as np
from PIL import Image

QR_PAYLOAD_PREFIX = "AADHAAR"
_CROP_PADDING = 12
_CROP_UPSCALE = 3.0


def _to_bgr(png: bytes) -> np.ndarray:
    with Image.open(BytesIO(png)) as image:
        rgb = np.array(image.convert("RGB"))
    return rgb[:, :, ::-1].copy()


def _decode_with_opencv(image_bgr: np.ndarray) -> str:
    import cv2

    detector = cv2.QRCodeDetector()
    # A QR that fills the frame decodes directly.
    data, _points, _ = detector.detectAndDecode(image_bgr)
    if data:
        return data
    # A QR sitting in a corner of a larger page is found, then decoded from an
    # upscaled crop — the reliable path for a small code on a big scan.
    found, points = detector.detect(image_bgr)
    if not found or points is None:
        return ""
    flat = points.reshape(-1, 2)
    height, width = image_bgr.shape[:2]
    x0 = max(0, int(flat[:, 0].min()) - _CROP_PADDING)
    y0 = max(0, int(flat[:, 1].min()) - _CROP_PADDING)
    x1 = min(width, int(flat[:, 0].max()) + _CROP_PADDING)
    y1 = min(height, int(flat[:, 1].max()) + _CROP_PADDING)
    crop = image_bgr[y0:y1, x0:x1]
    if crop.size == 0:
        return ""
    crop = cv2.resize(
        crop, None, fx=_CROP_UPSCALE, fy=_CROP_UPSCALE, interpolation=cv2.INTER_CUBIC
    )
    data, _points, _ = detector.detectAndDecode(crop)
    return data or ""


def parse_qr_payload(payload: str) -> Optional[Dict[str, str]]:
    """Turn our delimited payload into fields, or None if it is not one of ours.

    Returned keys are the catalog's own (`name`, `aadhaarNo`, `dob`, `gender`) so
    they line up with the printed field reads the check compares them against.
    """
    text = str(payload or "").strip()
    if not text.startswith(QR_PAYLOAD_PREFIX):
        return None
    fields: Dict[str, str] = {}
    for part in text.split("|")[1:]:
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        fields[key.strip()] = value.strip()
    key_by_payload = {
        "name": "name",
        "uid": "aadhaarNo",
        "dob": "dob",
        "gender": "gender",
    }
    parsed = {
        catalog_key: fields[payload_key]
        for payload_key, catalog_key in key_by_payload.items()
        if fields.get(payload_key)
    }
    return parsed or None


def decode_qr_fields(page_images: List[bytes]) -> Optional[Dict[str, str]]:
    """The QR payload fields from the first page that carries a readable one of ours.

    Returns None when no page holds a QR we can read and recognise. Any decode
    failure is swallowed to None: a document without a legible QR is a normal case,
    not an error, and the check downstream reports "no QR" rather than crashing.
    """
    for png in page_images:
        try:
            payload = _decode_with_opencv(_to_bgr(png))
        except Exception:
            continue
        parsed = parse_qr_payload(payload)
        if parsed is not None:
            return parsed
    return None
