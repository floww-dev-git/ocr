from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class PartyDTO:
    """One person or body on one side of a deed.

    `relation` and `relative_name` are not decoration: they are what tells two
    people apart when the same name appears across deeds, which is the whole basis
    of tracing a chain of title.
    """

    name: str
    name_original: Optional[str] = None
    relation: Optional[str] = None
    relative_name: Optional[str] = None
    address: Optional[str] = None
    pan: Optional[str] = None
    aadhaar: Optional[str] = None


@dataclass(frozen=True)
class PropertyInfoDTO:
    survey_no: Optional[str] = None
    plot_no: Optional[str] = None
    extent_text: Optional[str] = None
    extent_sq_yard: Optional[float] = None
    boundaries: Optional[str] = None
    locality: Optional[str] = None
    ulpin: Optional[str] = None


@dataclass(frozen=True)
class DeedRecordDTO:
    """One registered property document, read into structured form.

    Carried alongside the flat field values rather than instead of them. The flat
    values are what the officer reads and corrects; this is what the chain engine
    reasons over, because tracing title needs party *lists* and the deed numbers a
    recital cites, neither of which survives being flattened to one string.
    """

    doc_no: Optional[str] = None
    sro: Optional[str] = None
    registration_date: Optional[str] = None
    execution_date: Optional[str] = None
    deed_type: Optional[str] = None
    sellers: Tuple[PartyDTO, ...] = ()
    buyers: Tuple[PartyDTO, ...] = ()
    property_info: PropertyInfoDTO = field(default_factory=PropertyInfoDTO)
    consideration_text: Optional[str] = None
    consideration_inr: Optional[float] = None
    stamp_duty_text: Optional[str] = None
    estamp_no: Optional[str] = None
    # The deed numbers the recital cites as the seller's own source of title.
    prior_deed_refs: Tuple[str, ...] = ()
    executed_via_gpa: bool = False
