"""Risk & fraud scoring (Tier 3) — aggregates per-deed and cross-deed signals into a
single risk picture for the chain. Deterministic; explains every point it assigns.

This is the "why pay for this" layer: it surfaces what a tired reviewer skims past.
"""
from __future__ import annotations

from rapidfuzz import fuzz, utils

_PROC = utils.default_process

from schema import DeedRecord, SEV_HIGH, SEV_MEDIUM, SEV_LOW

_WEIGHT = {SEV_HIGH: 40, SEV_MEDIUM: 20, SEV_LOW: 8}


def _sig(severity, code, title, detail):
    return {"severity": severity, "code": code, "title": title, "detail": detail}


def compute_risk(deeds: list[DeedRecord], chain: dict) -> dict:
    signals: list[dict] = []
    by_id = {d.deed_id: d for d in deeds}
    ordered = [by_id[i] for i in chain.get("ordered_deed_ids", []) if i in by_id] or deeds

    # ---- per-deed signals ----
    for d in deeds:
        dt = (d.deed_type or "").lower()
        if d.executed_via_gpa or "power of attorney" in dt or dt.strip() == "gpa":
            signals.append(_sig(SEV_HIGH, "gpa_title", "Title via Power of Attorney",
                                 f"Deed {d.deed_id} ({d.doc_no or '?'}) passes title through a GPA — legally weak since the 2011 Suraj Lamp ruling."))
        if "agreement to sell" in dt or dt == "agreement":
            signals.append(_sig(SEV_HIGH, "agreement_only", "Agreement, not a conveyance",
                                 f"Deed {d.deed_id} is an Agreement to Sell — it does not by itself transfer ownership."))
        parties = (d.sellers or []) + (d.buyers or [])
        if parties and not any(p.pan or p.aadhaar for p in parties):
            signals.append(_sig(SEV_LOW, "no_id", "No party ID captured",
                                 f"Deed {d.deed_id}: no PAN/Govt-ID for any party — identity unverifiable."))

    # ---- cross-deed identity consistency ----
    pan_to_names: dict[str, set[str]] = {}
    for d in deeds:
        for p in (d.sellers or []) + (d.buyers or []):
            if p.pan:
                pan_to_names.setdefault(p.pan.upper(), set()).add(p.name)
    for pan, names in pan_to_names.items():
        if len(names) > 1 and max(fuzz.token_sort_ratio(a, b, processor=_PROC) for a in names for b in names if a != b) < 80:
            signals.append(_sig(SEV_MEDIUM, "pan_name_mismatch", "Same PAN, different names",
                                 f"PAN {pan} appears under differing names: {', '.join(sorted(names))}."))

    # ---- chain-derived signals ----
    c = chain.get("counts", {})
    if c.get("broken"):
        signals.append(_sig(SEV_HIGH, "broken_chain", "Broken ownership link",
                            f"{c['broken']} transfer(s) have no continuity — the chain does not hold as provided."))
    if c.get("gap"):
        signals.append(_sig(SEV_HIGH, "missing_deed", "Suspected missing deed",
                            f"{c['gap']} transfer(s) reference a deed not in the bundle or convey more extent than acquired."))
    if c.get("weak"):
        signals.append(_sig(SEV_MEDIUM, "weak_link", "Weak link needs review",
                            f"{c['weak']} link(s) rely on an approximate name match."))

    # ---- price anomaly (consideration should generally rise over time) ----
    priced = [(d.deed_id, d.consideration_inr) for d in ordered if d.consideration_inr]
    for (id_a, a), (id_b, b) in zip(priced, priced[1:]):
        if b < a * 0.6:
            signals.append(_sig(SEV_MEDIUM, "price_drop", "Sharp price drop",
                                f"Consideration fell from ₹{a:,.0f} ({id_a}) to ₹{b:,.0f} ({id_b}) — possible distress/benami/under-valuation."))

    # ---- score ----
    score = min(100, sum(_WEIGHT.get(s["severity"], 0) for s in signals))
    level = "High" if score >= 60 else "Medium" if score >= 25 else "Low"
    order = {SEV_HIGH: 0, SEV_MEDIUM: 1, SEV_LOW: 2}
    signals.sort(key=lambda s: order.get(s["severity"], 9))
    return {"score": score, "level": level, "signals": signals}
