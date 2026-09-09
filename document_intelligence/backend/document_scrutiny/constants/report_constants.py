import enum

from document_scrutiny.constants.chain_constants import FindingSeverity, LinkVerdict


class JourneyEntryKind(enum.Enum):
    OWNER = "owner"
    TRANSFER = "transfer"


class ReportVerdictLevel(enum.Enum):
    CLEAN = "clean"
    REVIEW = "review"
    BROKEN = "broken"


class JourneyVerdict(enum.Enum):
    """A transfer row's verdict. Extends the link verdicts with the two rows that are
    not links at all: the earliest deed, and an instrument that only grants authority."""

    ORIGIN = "origin"
    AUTHORITY = "authority"


UNKNOWN_PARTY_NAME = "Unknown"
UNNAMED_DEED = "Deed"
UNNAMED_AGREEMENT = "Agreement"

TITLE_OWNER_BADGE = "TITLE OWNER"
DEVELOPER_BADGE = "DEVELOPER"
MOTHER_DEED_BADGE = "MOTHER DEED"
NO_BADGE = ""

DEVELOPER_ROLE = "Today · developing"
DEVELOPER_META = "Holds development rights and a GPA — not the title owner"
AUTHORITY_NOTE = (
    "Authority to develop and sell on the owner's behalf — does not itself convey title."
)
ROOT_OF_TITLE_ROLE = "Root of title"
PREVIOUS_OWNER_META = "previous owner"
OWNER_ROLE = "Owner"
OWNER_SINCE_ROLE = "Owner since {year}"
ACQUIRED_FROM_META = "acquired from {name}"
EARLIEST_DEED_META = "earliest deed in the bundle — {described}"
UNKNOWN_YEAR = "?"

# Plain words for a verdict, with no glyphs: which icon to draw is the interface's
# business, and a payload that hard-codes one cannot be rendered any other way.
JOURNEY_LABELS = {
    JourneyVerdict.ORIGIN.value: "Origin — root deed",
    JourneyVerdict.AUTHORITY.value: "Authority only",
    LinkVerdict.LINKED.value: "Verified",
    LinkVerdict.WEAK.value: "Name to verify",
    LinkVerdict.GAP.value: "Missing deed",
    LinkVerdict.BROKEN.value: "Break",
}

ATTENTION_VERBS = {
    LinkVerdict.BROKEN.value: "RESOLVE",
    LinkVerdict.GAP.value: "RESOLVE",
    LinkVerdict.WEAK.value: "VERIFY",
}
ATTENTION_SEVERITIES = {
    LinkVerdict.BROKEN.value: FindingSeverity.HIGH.value,
    LinkVerdict.GAP.value: FindingSeverity.HIGH.value,
    LinkVerdict.WEAK.value: FindingSeverity.MEDIUM.value,
}
ATTENTION_ACTIONS = {
    LinkVerdict.GAP.value: (
        "Obtain the cited prior deed, or an encumbrance certificate for this survey "
        "number covering the gap period."
    ),
    LinkVerdict.BROKEN.value: (
        "Investigate the discontinuity — obtain the missing conveyance or a legal "
        "title opinion before relying on this chain."
    ),
    LinkVerdict.WEAK.value: (
        "Confirm identity against PAN or Aadhaar, or ask for a one-and-the-same "
        "affidavit."
    ),
}
DEFAULT_ATTENTION_ACTION = "Review with a legal expert."

BROKEN_HEADLINE = "The title chain is broken"
BROKEN_PLAIN = (
    "At least one ownership hand-off does not connect across {count} deeds — the "
    "chain does not hold as provided."
)
REVIEW_HEADLINE = "Title traces back to {root} — but {count} {things} {verb} checking"
REVIEW_PLAIN = (
    "Ownership flows through {count} registered deeds and reaches the current owner. "
    "Before it can be called clean, {reasons}."
)
CLEAN_HEADLINE = "Title traces cleanly from {root} to today"
CLEAN_PLAIN = (
    "Ownership flows through {count} registered deeds with no breaks and reaches the "
    "current owner."
)
NOTHING_TO_TRACE_HEADLINE = "No registered deed to trace"
NOTHING_TO_TRACE_PLAIN = (
    "Nothing attached to this application conveys title, so there is no chain to "
    "follow."
)
SINGLE_DEED_HEADLINE = "Only one registered deed — nothing to trace back through"
SINGLE_DEED_PLAIN = (
    "One deed conveys the property to the current owner, but the deeds behind it are "
    "not here, so the chain cannot be followed further back. Ask for the link documents."
)
# Written as independent clauses, not noun phrases, so REVIEW_PLAIN reads as a
# sentence whether it carries one reason or two. As bare noun phrases they produced
# "Before it can be called clean, a period that may be missing a deed." — which
# states nothing.
GAP_REASON = "a period may be missing a deed"
WEAK_REASON = "an ownership hand-off relies on an approximate name match"
THE_ROOT_DEED = "the root deed"
ONE_THING = "thing"
MANY_THINGS = "things"
# The verb has to agree with the count, or one finding reads "1 thing need checking".
ONE_THING_VERB = "needs"
MANY_THINGS_VERB = "need"
