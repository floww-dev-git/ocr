import enum


class LinkVerdict(enum.Enum):
    """How one transfer in the chain reconciles with the transfer before it."""

    LINKED = "linked"  # clean
    WEAK = "weak"  # reconciles, but with a caveat a human should read
    GAP = "gap"  # traces back, yet property, extent or recital is off
    BROKEN = "broken"  # no continuity of person at all


class ChainVerdict(enum.Enum):
    INTACT = "intact"
    REVIEW = "review"  # intact with caveats
    BROKEN = "broken"


class FindingSeverity(enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CLEAR = "clear"


class TitleRole(enum.Enum):
    """What a document does, which decides whether it can form a link at all.

    Grounded in Suraj Lamp: a power of attorney, an agreement to sell or a will
    does not by itself convey title, so none of them belongs in a chain of title.
    """

    TITLE = "title"  # sale / gift / partition / settlement / release — forms the chain
    AUTHORITY = "authority"  # GPA / development agreement / agreement to sell / will
    METADATA = "metadata"  # registration summary / index — not a deed at all


# Identity continuity is GRADUATED by name similarity, not binary. Carried from
# sale_deed_poc/build/poc/chain.py, and calibrated to rapidfuzz's own ratios: change
# the matcher and these numbers stop meaning what they mean.
NAME_STRONG_SCORE = 85  # >= this, the link is clean
NAME_WEAK_SCORE = 60  # in [WEAK, STRONG), a partial match -> review, never broken
NAME_CORROBORATION_FLOOR = 48  # a matching relative or address can rescue this far down
RELATIVE_NAME_CORROBORATION_SCORE = 80
ADDRESS_CORROBORATION_SCORE = 80
PROPERTY_MATCH_SCORE = 85
# 2% on extent arithmetic: a deed rounds its own area, and a rounding is not a gap.
EXTENT_TOLERANCE_FRACTION = 0.02

IDENTITY_SCORE_DECIMAL_PLACES = 0

# What the chain says when it has nothing to say, so a caller never special-cases it.
CLEAN_LINK_DETAIL = "Identity, property, recital and dates reconcile cleanly."

FINDING_TITLES = {
    LinkVerdict.BROKEN.value: "Broken link — no continuity",
    LinkVerdict.GAP.value: "Suspected missing deed",
    LinkVerdict.WEAK.value: "Weak link — verify",
    LinkVerdict.LINKED.value: "Link verified",
}

SEVERITY_BY_LINK_VERDICT = {
    LinkVerdict.BROKEN.value: FindingSeverity.HIGH.value,
    LinkVerdict.GAP.value: FindingSeverity.HIGH.value,
    LinkVerdict.WEAK.value: FindingSeverity.MEDIUM.value,
    LinkVerdict.LINKED.value: FindingSeverity.CLEAR.value,
}

SEVERITY_ORDER = (
    FindingSeverity.HIGH.value,
    FindingSeverity.MEDIUM.value,
    FindingSeverity.LOW.value,
    FindingSeverity.CLEAR.value,
)

METADATA_DEED_KINDS = (
    "registration summary",
    "registration detail",
    "link document summary",
    "index",
    "memo of",
)
AUTHORITY_DEED_KINDS = (
    "power of attorney",
    "gpa",
    "g.p.a",
    "i.g.p.a",
    "agreement",
    "will",
    "development agreement",
)
TITLE_DEED_KINDS = (
    "sale",
    "gift",
    "partition",
    "settlement",
    "release",
    "relinquish",
    "conveyance",
    "exchange",
)
CONVEYANCE_PHRASE = "sale deed"
AGREEMENT_TO_SELL_PHRASE = "agreement to sell"

DEED_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d-%b-%Y",
    "%d %B %Y",
    "%Y/%m/%d",
)
