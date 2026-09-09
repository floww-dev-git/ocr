"""Report assembly — combine extracted deeds + chain result into the final payload
the frontend renders. Presentation assembly only; no business logic.
"""
from __future__ import annotations

from schema import DeedRecord, OVERALL_INTACT, OVERALL_REVIEW, OVERALL_BROKEN
from risk import compute_risk
from roles import classify_role, ROLE_TITLE, ROLE_AUTHORITY, ROLE_METADATA
from chain import validate_chain, _parse_date

_OVERALL_LABEL = {
    OVERALL_INTACT: ("Chain intact", "All transfers reconcile cleanly. No action needed."),
    OVERALL_REVIEW: ("Review required", "The chain largely holds, but some links need a human to clear."),
    OVERALL_BROKEN: ("Chain broken", "At least one transfer has no continuity — the chain does not hold as provided."),
}


def _property_summary(deeds: list[DeedRecord]) -> dict:
    """Take the richest property description across the deeds (latest non-empty wins)."""
    summary = {"survey_no": None, "plot_no": None, "extent_text": None, "locality": None, "boundaries": None}
    for d in deeds:
        p = d.property
        for k in summary:
            v = getattr(p, k, None)
            if v:
                summary[k] = v
    return summary


def _pname(parties) -> dict:
    p = parties[0] if parties else None
    return {
        "name": (p.name if p else "Unknown"),
        "name_original": (p.name_original if p else None),
        "relative": (f"{p.relation} {p.relative_name}" if p and p.relation and p.relative_name else None),
        "extra": (len(parties) - 1) if parties else 0,
    }


def _year(d: DeedRecord) -> str | None:
    dt = _parse_date(d.registration_date or d.execution_date)
    return str(dt.year) if dt else None


def _dedup_by_doc(deeds: list[DeedRecord]) -> list[DeedRecord]:
    """Collapse documents that share a registration number (a bundle often photocopies the
    same deed twice / the inventory occasionally double-counts). Keep the higher-confidence copy."""
    import re
    out: list[DeedRecord] = []
    by_doc: dict[str, DeedRecord] = {}
    for d in deeds:
        key = re.sub(r"\s+", "", (d.doc_no or "")).lower()
        if not key:
            out.append(d)
            continue
        if key in by_doc:
            if (d.confidence or 0) > (by_doc[key].confidence or 0):
                out[out.index(by_doc[key])] = d
                by_doc[key] = d
            continue
        by_doc[key] = d
        out.append(d)
    return out


def build_report_v2(all_deeds: list[DeedRecord]) -> dict:
    """The intuitive report: classify documents by role, validate the chain on the
    title-conveying deeds ONLY, and produce an ownership-journey + plain-language verdict."""
    all_deeds = _dedup_by_doc(all_deeds)
    for d in all_deeds:
        d.doc_role = classify_role(d.deed_type, d.executed_via_gpa)

    title = [d for d in all_deeds if d.doc_role == ROLE_TITLE]
    authority = [d for d in all_deeds if d.doc_role == ROLE_AUTHORITY]
    metadata = [d for d in all_deeds if d.doc_role == ROLE_METADATA]

    chain = validate_chain(title) if len(title) >= 2 else {
        "ordered_deed_ids": [d.deed_id for d in title], "links": [], "findings": [],
        "counts": {}, "overall": OVERALL_REVIEW,
    }
    by_id = {d.deed_id: d for d in title}
    ordered = [by_id[i] for i in chain["ordered_deed_ids"] if i in by_id]
    links = chain["links"]
    counts = chain.get("counts", {})

    # ---- ownership journey (newest first) ----
    journey = []
    # authority layer on top (e.g. Development Agreement cum GPA → developer holds authority)
    auth_latest = sorted(authority, key=lambda d: (_parse_date(d.registration_date) or _parse_date("1900-01-01")))[-1] if authority else None
    if auth_latest:
        journey.append({"kind": "owner", "role": "Today · developing", "badge": "DEVELOPER",
                        "party": _pname(auth_latest.buyers),
                        "meta": "Holds development rights & GPA — not the title owner", "now": True})
        journey.append({"kind": "transfer", "verdict": "authority", "label": "▷ AUTHORITY ONLY",
                        "ref": f"{auth_latest.deed_type or 'Agreement'} · {auth_latest.doc_no or ''}",
                        "note": "Authority to develop & sell on the owner's behalf — does not itself convey title."})

    # title chain, newest → oldest
    if ordered:
        owners_seq = [("Owner", _pname(ordered[-1].buyers), not auth_latest)]  # current title owner
        # walk transfers from newest to oldest
        for k in range(len(ordered) - 1, -1, -1):
            deed = ordered[k]
            verdict = "origin" if k == 0 else (links[k - 1]["verdict"] if k - 1 < len(links) else "origin")
            note = " ".join((links[k - 1]["notes"] if k >= 1 and k - 1 < len(links) else [])) or None
            if k == len(ordered) - 1:
                journey.append({"kind": "owner", "role": f"Owner since {_year(deed) or '?'}",
                                "badge": "TITLE OWNER", "party": _pname(deed.buyers),
                                "meta": _pname(deed.sellers)["name"] and f"acquired from {_pname(deed.sellers)['name']}",
                                "now": not auth_latest})
            journey.append({"kind": "transfer", "verdict": verdict,
                            "label": _verdict_label(verdict),
                            "ref": f"{deed.deed_type or 'Deed'} · {deed.doc_no or ''}"
                                   + (f" · {deed.consideration_text}" if deed.consideration_text else ""),
                            "note": note, "id_score": links[k - 1].get("id_score") if k >= 1 and k - 1 < len(links) else None})
            seller = ordered[k].sellers
            role = "Root of title" if k == 0 else f"Owner"
            journey.append({"kind": "owner", "role": role + (f" · {_year(deed)}" if k == 0 else ""),
                            "badge": "MOTHER DEED" if k == 0 else "", "party": _pname(seller),
                            "meta": (f"earliest deed in the bundle — {deed.deed_type} {deed.doc_no}" if k == 0 else "previous owner")})

    # ---- verdict (plain language) ----
    need_review = counts.get("weak", 0) + counts.get("gap", 0)
    breaks = counts.get("broken", 0)
    root_year = _year(ordered[0]) if ordered else None
    cur_year = _year(ordered[-1]) if ordered else None
    if breaks:
        level, icon = "broken", "⛔"
        headline = "The title chain is broken"
        plain = f"At least one ownership hand-off does not connect across {len(title)} deeds — the chain does not hold as provided."
    elif need_review:
        level, icon = "review", "⚠️"
        bits = []
        if counts.get("gap"): bits.append("a period that may be missing a deed")
        if counts.get("weak"): bits.append("an ownership hand-off that relies on an approximate name match")
        headline = f"Title traces back to {root_year or 'the root deed'} — but {need_review} thing{'s' if need_review != 1 else ''} need checking"
        plain = (f"Ownership flows through {len(title)} registered deeds and reaches the current owner. "
                 f"Before it can be called clean, " + " and ".join(bits) + ".")
    else:
        level, icon = "clean", "✅"
        headline = f"Title traces cleanly from {root_year or 'the root'} to today"
        plain = f"Ownership flows through {len(title)} registered deeds with no breaks and reaches the current owner."

    # ---- attention list ----
    attention = []
    for f in chain.get("findings", []):
        if f["verdict"] in ("broken", "gap", "weak"):
            attention.append({
                "severity": {"broken": "high", "gap": "high", "weak": "medium"}[f["verdict"]],
                "verb": {"broken": "RESOLVE", "gap": "RESOLVE", "weak": "VERIFY"}[f["verdict"]],
                "title": f["title"], "detail": f["detail"],
                "action": _attention_action(f["verdict"]),
            })

    def _docrows(lst):
        return [{"deed_type": d.deed_type, "doc_no": d.doc_no, "date": d.registration_date or d.execution_date,
                 "is_root": ordered and d.deed_id == ordered[0].deed_id} for d in lst]

    return {
        "version": 2,
        "property": _property_summary(title or all_deeds),
        "verdict": {"level": level, "icon": icon, "headline": headline, "plain": plain},
        "stats": {"title_deeds": len(title), "span_from": root_year, "span_to": cur_year,
                  "need_review": need_review, "breaks": breaks},
        "authority": [{"deed_type": d.deed_type, "doc_no": d.doc_no,
                       "owner": _pname(d.sellers)["name"], "holder": _pname(d.buyers)["name"]} for d in authority],
        "journey": journey,
        "docs_by_role": {"title": _docrows(title), "authority": _docrows(authority), "metadata": _docrows(metadata)},
        "attention": attention,
    }


def _verdict_label(v: str) -> str:
    return {"origin": "ORIGIN · root deed", "linked": "✓ VERIFIED", "weak": "⚠ NAME TO VERIFY",
            "gap": "⛳ MISSING DEED", "broken": "⛔ BREAK", "authority": "▷ AUTHORITY ONLY"}.get(v, v)


def _attention_action(v: str) -> str:
    return {
        "gap": "Obtain the cited prior deed, or an Encumbrance Certificate for this survey number covering the gap period.",
        "broken": "Investigate the discontinuity — obtain the missing conveyance or a legal title opinion before relying on this chain.",
        "weak": "Confirm identity via PAN/Aadhaar or a one-and-the-same affidavit.",
    }.get(v, "Review with a legal expert.")


def build_report(deeds: list[DeedRecord], chain: dict) -> dict:
    label, blurb = _OVERALL_LABEL.get(chain["overall"], ("Unknown", ""))
    confs = [d.confidence for d in deeds if d.confidence]
    return {
        "overall": chain["overall"],
        "overall_label": label,
        "overall_blurb": blurb,
        "counts": chain["counts"],
        "property": _property_summary(deeds),
        "glance": {
            "deeds": len(deeds),
            "span_from": min((d.registration_date or "" for d in deeds), default=""),
            "span_to": max((d.registration_date or "" for d in deeds), default=""),
            "avg_confidence": round(sum(confs) / len(confs), 2) if confs else None,
        },
        "links": chain["links"],
        "findings": chain["findings"],
        "ordered_deed_ids": chain["ordered_deed_ids"],
        "risk": compute_risk(deeds, chain),
    }
