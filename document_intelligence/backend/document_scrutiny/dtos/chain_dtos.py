from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple

from document_extraction.dtos.deed_record_dtos import DeedRecordDTO
from document_scrutiny.constants.chain_constants import TitleRole

TITLE_ROLE = TitleRole.TITLE.value


@dataclass(frozen=True)
class ChainDeedDTO:
    """One registered deed offered to the chain, and where the officer will find it.

    The record is what the chain reasons over; the document id and page range are how
    a verdict points back at a row the officer can open.
    """

    document_id: str
    filename: str
    deed_record: DeedRecordDTO
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    # How well this deed was read. Only used to choose between two copies of the same
    # registration number, which a bundle photocopied twice will produce.
    read_confidence: float = 0.0


@dataclass(frozen=True)
class LinkChecksDTO:
    """The named questions asked of one transfer.

    `None` means the question could not be asked — an extent that was never read, a
    recital on a deed whose seller matches nobody. That is deliberately not the same
    as `False`, which means the deed answered and the answer is wrong.
    """

    identity: bool
    property_agrees: bool
    extent_within_source: Optional[bool] = None
    recital_cites_source: Optional[bool] = None
    dates_in_order: Optional[bool] = None

    def asked(self) -> Mapping[str, bool]:
        """Only the questions this link could actually be asked."""
        answers = {
            "identity": self.identity,
            "property": self.property_agrees,
            "extent": self.extent_within_source,
            "recital": self.recital_cites_source,
            "dates": self.dates_in_order,
        }
        return {name: answer for name, answer in answers.items() if answer is not None}

    def all_agree(self) -> bool:
        return all(self.asked().values())


@dataclass(frozen=True)
class ChainLinkDTO:
    from_document_id: str
    to_document_id: str
    from_doc_no: Optional[str]
    to_doc_no: Optional[str]
    verdict: str
    identity_score: int
    checks: LinkChecksDTO
    notes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ChainFindingDTO:
    severity: str
    verdict: str
    title: str
    detail: str


@dataclass(frozen=True)
class ChainOfTitleRequestDTO:
    thread_id: str


@dataclass(frozen=True)
class ChainOfTitleDTO:
    ordered_document_ids: Tuple[str, ...] = ()
    links: Tuple[ChainLinkDTO, ...] = ()
    counts: Mapping[str, int] = field(default_factory=dict)
    overall: str = ""
    findings: Tuple[ChainFindingDTO, ...] = ()
    # What each deed offered to the chain turned out to be, in the order offered.
    # A power of attorney is not a missing link; it is not a link.
    roles_by_document_id: Mapping[str, str] = field(default_factory=dict)
    # Copies of a deed already counted under the same registration number. A bundle
    # photocopies the same deed twice often enough to matter.
    duplicate_document_ids: Tuple[str, ...] = ()

    @property
    def excluded_document_ids(self) -> Tuple[str, ...]:
        """Deeds the chain set aside because they convey nothing."""
        return tuple(
            document_id
            for document_id, role in self.roles_by_document_id.items()
            if role != TITLE_ROLE
        )
