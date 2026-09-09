"""Classify a document by its TITLE ROLE — does it convey title, grant authority, or is it metadata?

This is the basis of the intuitive report: only title-conveying deeds form the chain;
authority instruments (GPA / Development Agreement / Agreement-to-Sell / Will) and metadata
(summary/index sheets) are shown separately and EXCLUDED from the chain. Grounded in research/01
(Suraj Lamp: a GPA/agreement/will does not by itself convey title; a DA-cum-GPA is authority).
"""
from __future__ import annotations

ROLE_TITLE = "title"        # sale / gift / partition / settlement / release — forms the chain
ROLE_AUTHORITY = "authority"  # GPA / Development Agreement / Agreement-to-Sell / Will — not a conveyance
ROLE_METADATA = "metadata"  # registration-summary / index / EC — not a deed at all

_METADATA_KINDS = ("registration summary", "registration detail", "link document summary", "index", "memo of")
_AUTHORITY_KINDS = ("power of attorney", "gpa", "g.p.a", "i.g.p.a", "agreement", "will", "development agreement")
_TITLE_KINDS = ("sale", "gift", "partition", "settlement", "release", "relinquish", "conveyance", "exchange")


def classify_role(deed_type: str | None, executed_via_gpa: bool = False) -> str:
    dt = (deed_type or "").lower()
    if not dt:
        return ROLE_TITLE  # unknown — treat as a deed (will likely surface as low-confidence)
    if any(k in dt for k in _METADATA_KINDS):
        return ROLE_METADATA
    # authority is checked BEFORE title: "Development Agreement cum GPA" / "Agreement to Sell"
    # contain no title keyword, but "cum Sale"... is rare; a pure conveyance never matches these.
    if any(k in dt for k in _AUTHORITY_KINDS) and not _is_conveyance_cum(dt):
        return ROLE_AUTHORITY
    if any(k in dt for k in _TITLE_KINDS):
        return ROLE_TITLE
    return ROLE_TITLE


def _is_conveyance_cum(dt: str) -> bool:
    # a true "Sale cum ..." conveyance still conveys; keep it as title
    return "sale deed" in dt and "agreement to sell" not in dt
