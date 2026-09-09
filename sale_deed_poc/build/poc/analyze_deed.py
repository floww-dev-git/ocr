"""Per-deed analysis (Tier 1) — checks each deed in isolation, before chain logic.

Pure code, deterministic. Returns a list of flags (dicts) per deed.
"""
from __future__ import annotations

from schema import DeedRecord, SEV_HIGH, SEV_MEDIUM, SEV_LOW

# Instruments that do NOT convey clean registered title.
NON_SALE_TYPES = ("gpa", "power of attorney", "agreement to sell", "agreement", "will", "unregistered")


def _flag(severity: str, code: str, message: str) -> dict:
    return {"severity": severity, "code": code, "message": message}


def analyze_deed(deed: DeedRecord) -> list[dict]:
    flags: list[dict] = []
    dt = (deed.deed_type or "").lower()

    # 1. Is this actually a title-conveying sale?
    if dt and not ("sale" in dt and "agreement" not in dt):
        if any(t in dt for t in NON_SALE_TYPES):
            flags.append(_flag(
                SEV_HIGH, "not_a_sale",
                f"Instrument is '{deed.deed_type}', not a registered sale deed — it may not convey clean title.",
            ))

    # 2. Executed via power of attorney → higher risk
    if deed.executed_via_gpa:
        flags.append(_flag(
            SEV_MEDIUM, "gpa_execution",
            "Executed by a power-of-attorney holder rather than the owner in person.",
        ))

    # 3. Completeness of the registration identity
    missing = [name for name, val in (("doc_no", deed.doc_no),
                                      ("registration_date", deed.registration_date),
                                      ("sro", deed.sro)) if not val]
    if missing:
        flags.append(_flag(
            SEV_MEDIUM, "incomplete_registration",
            f"Missing registration identifier(s): {', '.join(missing)}.",
        ))

    # 4. Property identity present
    if not (deed.property.survey_no or deed.property.plot_no):
        flags.append(_flag(SEV_LOW, "no_property_id", "No survey/plot number extracted for the property."))
    if deed.property.extent_sqyd is None:
        flags.append(_flag(SEV_LOW, "no_extent", "Property extent could not be normalised — extent checks limited."))

    # 5. Parties present
    if not deed.sellers or not deed.buyers:
        flags.append(_flag(SEV_MEDIUM, "missing_party", "Seller or buyer could not be extracted."))

    # 6. Low-confidence extraction
    if deed.confidence and deed.confidence < 0.75:
        flags.append(_flag(
            SEV_LOW, "low_confidence",
            f"Extraction confidence {deed.confidence:.2f}"
            + (f"; review: {', '.join(deed.low_confidence_fields)}" if deed.low_confidence_fields else "."),
        ))

    return flags
