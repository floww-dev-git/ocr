import enum

from document_scrutiny.constants.chain_constants import FindingSeverity


class RiskLevel(enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class RiskSignalCode(enum.Enum):
    """Why a point was assigned. Every signal names itself, so a score can be argued with."""

    TITLE_VIA_GPA = "gpa_title"
    AGREEMENT_ONLY = "agreement_only"
    NO_PARTY_IDENTIFIER = "no_id"
    SAME_IDENTIFIER_DIFFERENT_NAMES = "pan_name_mismatch"
    BROKEN_CHAIN = "broken_chain"
    MISSING_DEED = "missing_deed"
    WEAK_LINK = "weak_link"
    PRICE_DROP = "price_drop"


# Carried from sale_deed_poc/build/poc/risk.py.
WEIGHT_BY_SEVERITY = {
    FindingSeverity.HIGH.value: 40,
    FindingSeverity.MEDIUM.value: 20,
    FindingSeverity.LOW.value: 8,
}
MAXIMUM_RISK_SCORE = 100
HIGH_RISK_FLOOR = 60
MEDIUM_RISK_FLOOR = 25

# A consideration falling below this share of the previous one is worth a look:
# a distress sale, a benami arrangement or an under-valuation all look like this.
PRICE_DROP_FRACTION = 0.6
# Two names on one identifier are the same person if they are at least this alike.
SAME_PERSON_NAME_SCORE = 80

POWER_OF_ATTORNEY_PHRASES = ("power of attorney", "gpa")
AGREEMENT_ONLY_PHRASES = ("agreement to sell", "agreement")

RISK_SIGNAL_TITLES = {
    RiskSignalCode.TITLE_VIA_GPA.value: "Title via power of attorney",
    RiskSignalCode.AGREEMENT_ONLY.value: "Agreement, not a conveyance",
    RiskSignalCode.NO_PARTY_IDENTIFIER.value: "No party identifier captured",
    RiskSignalCode.SAME_IDENTIFIER_DIFFERENT_NAMES.value: (
        "Same PAN, different names"
    ),
    RiskSignalCode.BROKEN_CHAIN.value: "Broken ownership link",
    RiskSignalCode.MISSING_DEED.value: "Suspected missing deed",
    RiskSignalCode.WEAK_LINK.value: "Weak link needs review",
    RiskSignalCode.PRICE_DROP.value: "Sharp price drop",
}
