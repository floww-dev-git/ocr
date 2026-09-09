"""Chain validation (Tier 2) — the deterministic core IP.

Given a list of DeedRecords, sort them into a timeline and verify each consecutive
transfer for continuity of identity, property, extent, recital and time. Emits a
per-link verdict, an overall verdict, and findings with evidence.

No model calls here — this is the explainable, testable judgement layer.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from rapidfuzz import fuzz, utils

_PROC = utils.default_process  # lowercase + strip punctuation ("M/S", "&") so case/format never blocks a match

from schema import (
    DeedRecord, Party,
    LINK_LINKED, LINK_WEAK, LINK_GAP, LINK_BROKEN,
    OVERALL_INTACT, OVERALL_REVIEW, OVERALL_BROKEN,
    SEV_HIGH, SEV_MEDIUM, SEV_CLEAR,
)

# identity continuity is GRADUATED by name similarity, not binary:
NAME_STRONG = 85        # >= → strong match, link is clean
NAME_WEAK = 60          # NAME_WEAK..NAME_STRONG → partial match → WEAK (review), not broken
NAME_CORROB_FLOOR = 48  # a relative/address match can rescue a slightly lower score into 'weak'
EXTENT_TOL = 0.02       # 2% tolerance on extent arithmetic


# ---------- helpers ----------

def _parse_date(s: str | None) -> date | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %B %Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    m = re.search(r"(\d{4})", s)              # last resort: just the year
    if m:
        try:
            return date(int(m.group(1)), 1, 1)
        except ValueError:
            return None
    return None


def _norm_doc(d: str | None) -> str:
    return re.sub(r"\s+", "", (d or "")).lower()


def _name_blob(p: Party) -> str:
    return " ".join(x for x in (p.name, p.relative_name) if x).strip()


def best_person_match(a: list[Party], b: list[Party]) -> tuple[float, bool]:
    """Best name similarity between two party lists, and whether a relative/address corroborates it."""
    best = 0.0
    corroborated = False
    for pa in a:
        for pb in b:
            # score on the NAME only. Use the max of:
            #  - token_sort_ratio: full-string similarity (catches Lakshmi/Laxmi as weak), and
            #  - token_set_ratio: subset/overlap (catches a buyer's full name CONTAINED inside a
            #    multi-party seller string, e.g. "Arun Menon" inside "Zenith Traders, Arun Menon").
            na, nb = pa.name or "", pb.name or ""
            score = max(fuzz.token_sort_ratio(na, nb, processor=_PROC),
                        fuzz.token_set_ratio(na, nb, processor=_PROC))
            if score > best:
                best = score
                rel_ok = bool(pa.relative_name and pb.relative_name
                              and fuzz.token_sort_ratio(pa.relative_name, pb.relative_name, processor=_PROC) >= 80)
                addr_ok = bool(pa.address and pb.address
                               and fuzz.partial_ratio(pa.address, pb.address, processor=_PROC) >= 80)
                corroborated = rel_ok or addr_ok
    return best, corroborated


def _same_property(a: DeedRecord, b: DeedRecord) -> bool | None:
    """True (match) / False (identifiers present but differ) / None (can't tell — not extracted)."""
    pa, pb = a.property, b.property
    # token_set_ratio catches a single survey contained in a combined/amalgamated deed
    # (e.g. "10" inside "Sy. 10, 11 & 12") — the property analogue of the name-overlap fix.
    def _match(x, y):
        return max(fuzz.token_sort_ratio(x, y, processor=_PROC),
                   fuzz.token_set_ratio(x, y, processor=_PROC)) >= 85
    if pa.survey_no and pb.survey_no:
        return _match(pa.survey_no, pb.survey_no)
    if pa.plot_no and pb.plot_no:
        return _match(str(pa.plot_no), str(pb.plot_no))
    return None  # unknown — don't penalise a link just because survey/plot wasn't read


# ---------- the link check ----------

def _cites_any(cur: DeedRecord, priors: list[DeedRecord]) -> bool:
    """Does cur's recital cite a prior deed that IS in this bundle?"""
    cited = {_norm_doc(r) for r in cur.prior_deed_refs}
    return any(p.doc_no and _norm_doc(p.doc_no) in cited for p in priors)


def _check_link(prev: DeedRecord, cur: DeedRecord, priors: list[DeedRecord]) -> dict:
    """Verify cur's seller traces back to a PRIOR acquisition. `prev` is the immediately
    previous deed (for the timeline); `priors` is every deed before cur — which lets us
    handle a buyer who aggregated land from MULTIPLE sellers across MULTIPLE deeds."""
    checks: dict[str, bool] = {}
    notes: list[str] = []
    cur_s = cur.sellers[0].name if cur.sellers else "?"

    # identity continuity: cur's seller should be the buyer of SOME prior deed FOR THE SAME PARCEL
    # (not just `prev`). A prior purchase of a DIFFERENT survey/plot does not count — title is per-parcel.
    best_score, best_corrob, best_src = 0.0, False, None
    for p in priors:
        if _same_property(p, cur) is False:
            continue  # same person perhaps, but a different property → not this parcel's chain
        s, c = best_person_match(p.buyers, cur.sellers)
        if s > best_score:
            best_score, best_corrob, best_src = s, c, p
    score = best_score
    src = best_src or prev  # the deed cur's seller most likely acquired this parcel from

    if score >= NAME_STRONG:
        identity = "match"
        if best_src is not None and best_src is not prev:
            notes.append(f"Seller continues from {best_src.doc_no} (an earlier purchase, not the immediately previous deed).")
    elif score >= NAME_WEAK or (best_corrob and score >= NAME_CORROB_FLOOR):
        identity = "weak"
        notes.append(f"Approximate name match ({score:.0f}/100) for seller '{cur_s}' — verify this is the same person.")
    else:
        # seller is not a prior buyer in the bundle → a NEW/original holding entering the chain
        # (normal when land is aggregated from several different sellers), unless cur claims an
        # in-bundle source it doesn't actually match.
        identity = "new_root"
        notes.append(f"Seller '{cur_s}' is not a prior owner in this bundle — treated as a new/original holding "
                     f"(normal when parcels are aggregated from multiple sellers).")
    checks["identity"] = identity != "new_root" or not _cites_any(cur, priors)

    # property continuity (tri-state: only a genuine difference counts against the link)
    prop = _same_property(src, cur)
    checks["property"] = prop is not False
    if prop is False:
        notes.append("Property identifiers (survey/plot) differ from the source deed.")

    # extent arithmetic — the AGGREGATE rule: cur may sell up to the SUM of everything its
    # seller acquired across ALL prior deeds (multiple purchases build a larger land right).
    sold = cur.property.extent_sqyd
    total_acquired, have_acq = 0.0, False
    for p in priors:
        if _same_property(p, cur) is False:
            continue  # only sum prior purchases of the SAME parcel
        s, _ = best_person_match(p.buyers, cur.sellers)
        if s >= NAME_WEAK and p.property.extent_sqyd:
            total_acquired += p.property.extent_sqyd
            have_acq = True
    if sold is not None and have_acq:
        if sold > total_acquired * (1 + EXTENT_TOL):
            checks["extent"] = False
            notes.append(
                f"Conveys {sold:g} sq.yd but the seller acquired only {total_acquired:g} sq.yd in total "
                f"across all prior purchases — the extra extent has no source deed in this bundle."
            )
        else:
            checks["extent"] = True

    # recital linkage: cur should cite its source deed's number
    src_doc = _norm_doc(src.doc_no)
    cited = {_norm_doc(r) for r in cur.prior_deed_refs}
    if src_doc and identity in ("match", "weak"):
        checks["recital"] = src_doc in cited
        if not checks["recital"]:
            extra = [r for r in cur.prior_deed_refs if _norm_doc(r) not in {src_doc}]
            notes.append(
                f"{cur.doc_no or 'Deed'} does not cite {src.doc_no} as its source of title"
                + (f"; it cites {', '.join(extra)} (not in bundle)." if extra else ".")
            )

    # temporal sanity
    dp, dc = _parse_date(prev.registration_date), _parse_date(cur.registration_date)
    if dp and dc:
        checks["dates"] = dc >= dp
        if not checks["dates"]:
            notes.append(f"{cur.doc_no} is dated before {prev.doc_no}.")

    # ---- roll up to a verdict ----
    extent_fail = checks.get("extent") is False
    recital_fail = checks.get("recital") is False
    if identity == "new_root" and _cites_any(cur, priors):
        verdict = LINK_BROKEN            # claims an in-bundle source but its seller matches no prior buyer
    elif prop is False or extent_fail or (recital_fail and _missing_intermediate(cur, prev)):
        verdict = LINK_GAP               # owner traces back, but property/extent/recital is off → review
    elif identity in ("weak", "new_root") or notes:
        verdict = LINK_WEAK              # partial match / new holding / minor caveats → review
    else:
        verdict = LINK_LINKED

    return {
        "from_deed": prev.deed_id,
        "to_deed": cur.deed_id,
        "deed_no": cur.doc_no,
        "checks": checks,
        "id_score": round(score),
        "verdict": verdict,
        "notes": notes,
    }


def _missing_intermediate(cur: DeedRecord, prev: DeedRecord) -> bool:
    """cur cites a prior deed that is neither prev nor in scope → a deed is probably missing."""
    cited = {_norm_doc(r) for r in cur.prior_deed_refs}
    return bool(cited) and _norm_doc(prev.doc_no) not in cited


# ---------- public API ----------

def validate_chain(deeds: list[DeedRecord]) -> dict:
    ordered = sorted(deeds, key=lambda d: (_parse_date(d.registration_date) or date.min))

    # each link checks ordered[i+1] against its immediate predecessor (for the timeline) AND
    # against every prior deed (ordered[:i+1]) so aggregated/multi-seller acquisitions resolve.
    links = [_check_link(ordered[i], ordered[i + 1], ordered[:i + 1]) for i in range(len(ordered) - 1)]

    counts = {LINK_LINKED: 0, LINK_WEAK: 0, LINK_GAP: 0, LINK_BROKEN: 0}
    for ln in links:
        counts[ln["verdict"]] += 1

    if counts[LINK_BROKEN]:
        overall = OVERALL_BROKEN
    elif counts[LINK_GAP] or counts[LINK_WEAK]:
        overall = OVERALL_REVIEW
    else:
        overall = OVERALL_INTACT

    findings = _build_findings(links, ordered)

    return {
        "ordered_deed_ids": [d.deed_id for d in ordered],
        "links": links,
        "counts": counts,
        "overall": overall,
        "findings": findings,
    }


def _build_findings(links: list[dict], ordered: list[DeedRecord]) -> list[dict]:
    findings: list[dict] = []
    for ln in links:
        sev = {LINK_BROKEN: SEV_HIGH, LINK_GAP: SEV_HIGH, LINK_WEAK: SEV_MEDIUM, LINK_LINKED: SEV_CLEAR}[ln["verdict"]]
        title = {
            LINK_BROKEN: "Broken link — no continuity",
            LINK_GAP: "Suspected missing deed",
            LINK_WEAK: "Weak link — verify",
            LINK_LINKED: "Link verified",
        }[ln["verdict"]]
        findings.append({
            "severity": sev,
            "verdict": ln["verdict"],
            "title": f"{title} ({ln['from_deed']} → {ln['to_deed']})",
            "detail": " ".join(ln["notes"]) or "Identity, property, recital and dates reconcile cleanly.",
        })
    # high severity first
    order = {SEV_HIGH: 0, SEV_MEDIUM: 1, "low": 2, SEV_CLEAR: 3}
    findings.sort(key=lambda f: order.get(f["severity"], 9))
    return findings
