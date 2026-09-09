"""Serves the synthetic Aadhaar specimens so the demo can load a scenario in one
click, instead of the reviewer hunting for a file to drag in.

Read-only, and scoped to the one generated specimen directory: it lists the
scenarios and streams a named specimen PDF. Nothing here is part of the scrutiny
engine — it exists only to drive the showcase (ADR-013).
"""
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpRequest, HttpResponseNotFound, JsonResponse
from django.views.decorators.http import require_GET

_SAMPLES_ROOT = Path(settings.BASE_DIR) / "samples" / "aadhaar"

# The scenarios, in the order they tell the capability story. Each names the
# specimen file and what it is built to demonstrate.
_SCENARIOS = (
    {
        "id": "clean",
        "filename": "aadhaar_clean.pdf",
        "label": "Clean Aadhaar",
        "demonstrates": "Everything agrees: extraction, checksum, QR, department.",
    },
    {
        "id": "name_typo",
        "filename": "aadhaar_name_typo.pdf",
        "label": "Misread name",
        "demonstrates": (
            "The printed name is a near-match to the application — flagged for "
            "review, not rejected, while the QR and the department read it as the "
            "same person."
        ),
    },
    {
        "id": "tampered_qr",
        "filename": "aadhaar_tampered_qr.pdf",
        "label": "Tampered — QR contradicts print",
        "demonstrates": "The QR carries the original identity the print was altered from.",
    },
    {
        "id": "invalid_number",
        "filename": "aadhaar_invalid_number.pdf",
        "label": "Invalid number",
        "demonstrates": "The number fails its Verhoeff checksum.",
    },
    {
        "id": "impossible_dob",
        "filename": "aadhaar_impossible_dob.pdf",
        "label": "Impossible date of birth",
        "demonstrates": (
            "The date of birth is in the future — the document contradicts itself, "
            "caught from the document alone."
        ),
    },
    {
        "id": "mismatch",
        "filename": "aadhaar_mismatch.pdf",
        "label": "Wrong person",
        "demonstrates": "Name and date of birth differ from the application.",
    },
    {
        "id": "poor_scan",
        "filename": "aadhaar_poor_scan.pdf",
        "label": "Poor-quality scan",
        "demonstrates": "The scan is too blurred to rely on.",
    },
)

_SCENARIOS_BY_FILENAME = {scenario["filename"]: scenario for scenario in _SCENARIOS}


@require_GET
def list_aadhaar_specimens(request: HttpRequest) -> JsonResponse:
    available = [
        scenario
        for scenario in _SCENARIOS
        if (_SAMPLES_ROOT / scenario["filename"]).is_file()
    ]
    return JsonResponse({"scenarios": available})


@require_GET
def get_aadhaar_specimen(request: HttpRequest, filename: str):
    # Only names this view knows are served, so the route cannot be used to read
    # arbitrary files.
    if filename not in _SCENARIOS_BY_FILENAME:
        return HttpResponseNotFound("Unknown specimen.")
    path = _SAMPLES_ROOT / filename
    if not path.is_file():
        return HttpResponseNotFound("Specimen not generated.")
    return FileResponse(path.open("rb"), content_type="application/pdf")
