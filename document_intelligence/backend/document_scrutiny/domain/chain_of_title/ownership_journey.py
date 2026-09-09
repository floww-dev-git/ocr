from typing import List, Optional, Sequence

from document_extraction.dtos.deed_record_dtos import PartyDTO
from document_scrutiny.constants.report_constants import (
    ACQUIRED_FROM_META,
    AUTHORITY_NOTE,
    DEVELOPER_BADGE,
    DEVELOPER_META,
    DEVELOPER_ROLE,
    EARLIEST_DEED_META,
    JOURNEY_LABELS,
    MOTHER_DEED_BADGE,
    NO_BADGE,
    OWNER_ROLE,
    OWNER_SINCE_ROLE,
    PREVIOUS_OWNER_META,
    ROOT_OF_TITLE_ROLE,
    TITLE_OWNER_BADGE,
    UNKNOWN_PARTY_NAME,
    UNKNOWN_YEAR,
    UNNAMED_AGREEMENT,
    UNNAMED_DEED,
    JourneyEntryKind,
    JourneyVerdict,
)
from document_scrutiny.domain.chain_of_title.deed_dates import DeedDates
from document_scrutiny.dtos.chain_dtos import ChainDeedDTO, ChainLinkDTO
from document_scrutiny.dtos.ownership_report_dtos import (
    JourneyEntryDTO,
    PartySummaryDTO,
)


class OwnershipJourney:
    """The property's ownership as a sequence, read newest first.

    Owners and the transfers between them alternate down one list, because that is how
    a person checks a chain: who holds it now, how they got it, and who held it before.

    Carried from sale_deed_poc/build/poc/report.py::build_report_v2.
    """

    @classmethod
    def compose(
        cls,
        ordered: Sequence[ChainDeedDTO],
        links: Sequence[ChainLinkDTO],
        authority: Sequence[ChainDeedDTO],
    ) -> Sequence[JourneyEntryDTO]:
        entries: List[JourneyEntryDTO] = []
        latest_authority = cls._latest(authority)
        if latest_authority is not None:
            entries.extend(cls._authority_entries(deed=latest_authority))
        entries.extend(
            cls._title_entries(
                ordered=ordered,
                links=links,
                someone_else_holds_authority=latest_authority is not None,
            )
        )
        return tuple(entries)

    @classmethod
    def summarise_party(cls, parties: Sequence[PartyDTO]) -> PartySummaryDTO:
        """Names the first party and says how many others stood with them.

        A deed with four sellers is a real thing, and listing only the first without
        saying so would quietly hide three owners.
        """
        party = parties[0] if parties else None
        if party is None:
            return PartySummaryDTO(name=UNKNOWN_PARTY_NAME)
        return PartySummaryDTO(
            name=party.name or UNKNOWN_PARTY_NAME,
            name_original=party.name_original,
            relative=cls._describe_relative(party),
            others_count=max(0, len(parties) - 1),
        )

    @staticmethod
    def _describe_relative(party: PartyDTO) -> Optional[str]:
        if not party.relation or not party.relative_name:
            return None
        return f"{party.relation} {party.relative_name}"

    @staticmethod
    def _latest(deeds: Sequence[ChainDeedDTO]) -> Optional[ChainDeedDTO]:
        if not deeds:
            return None
        return sorted(
            deeds,
            key=lambda deed: DeedDates.sort_key(deed.deed_record.registration_date),
        )[-1]

    @classmethod
    def _authority_entries(cls, deed: ChainDeedDTO) -> List[JourneyEntryDTO]:
        """An instrument that grants authority sits above the title, not inside it."""
        record = deed.deed_record
        return [
            JourneyEntryDTO(
                kind=JourneyEntryKind.OWNER.value,
                role=DEVELOPER_ROLE,
                badge=DEVELOPER_BADGE,
                party=cls.summarise_party(record.buyers),
                meta=DEVELOPER_META,
                is_current=True,
            ),
            JourneyEntryDTO(
                kind=JourneyEntryKind.TRANSFER.value,
                verdict=JourneyVerdict.AUTHORITY.value,
                label=JOURNEY_LABELS[JourneyVerdict.AUTHORITY.value],
                reference=cls._reference(
                    described=record.deed_type or UNNAMED_AGREEMENT,
                    doc_no=record.doc_no,
                    consideration=None,
                ),
                note=AUTHORITY_NOTE,
            ),
        ]

    @classmethod
    def _title_entries(
        cls,
        ordered: Sequence[ChainDeedDTO],
        links: Sequence[ChainLinkDTO],
        someone_else_holds_authority: bool,
    ) -> List[JourneyEntryDTO]:
        entries: List[JourneyEntryDTO] = []
        # Walked newest to oldest: each deed contributes the transfer it made and the
        # owner who made it, ending at the earliest deed in the bundle.
        for index in range(len(ordered) - 1, -1, -1):
            deed = ordered[index]
            incoming = links[index - 1] if 0 < index <= len(links) else None
            if index == len(ordered) - 1:
                entries.append(
                    cls._current_owner_entry(
                        deed=deed,
                        someone_else_holds_authority=someone_else_holds_authority,
                    )
                )
            entries.append(cls._transfer_entry(deed=deed, incoming=incoming))
            entries.append(cls._previous_owner_entry(deed=deed, is_root=index == 0))
        return entries

    @classmethod
    def _current_owner_entry(
        cls, deed: ChainDeedDTO, someone_else_holds_authority: bool
    ) -> JourneyEntryDTO:
        record = deed.deed_record
        seller = cls.summarise_party(record.sellers)
        return JourneyEntryDTO(
            kind=JourneyEntryKind.OWNER.value,
            role=OWNER_SINCE_ROLE.format(year=cls._year(deed) or UNKNOWN_YEAR),
            badge=TITLE_OWNER_BADGE,
            party=cls.summarise_party(record.buyers),
            meta=ACQUIRED_FROM_META.format(name=seller.name),
            is_current=not someone_else_holds_authority,
        )

    @classmethod
    def _transfer_entry(
        cls, deed: ChainDeedDTO, incoming: Optional[ChainLinkDTO]
    ) -> JourneyEntryDTO:
        record = deed.deed_record
        verdict = (
            incoming.verdict if incoming is not None else JourneyVerdict.ORIGIN.value
        )
        note = " ".join(incoming.notes) if incoming is not None else ""
        return JourneyEntryDTO(
            kind=JourneyEntryKind.TRANSFER.value,
            verdict=verdict,
            label=JOURNEY_LABELS.get(verdict, verdict),
            reference=cls._reference(
                described=record.deed_type or UNNAMED_DEED,
                doc_no=record.doc_no,
                consideration=record.consideration_text,
            ),
            note=note or None,
            identity_score=incoming.identity_score if incoming is not None else None,
        )

    @classmethod
    def _previous_owner_entry(
        cls, deed: ChainDeedDTO, is_root: bool
    ) -> JourneyEntryDTO:
        record = deed.deed_record
        if not is_root:
            return JourneyEntryDTO(
                kind=JourneyEntryKind.OWNER.value,
                role=OWNER_ROLE,
                badge=NO_BADGE,
                party=cls.summarise_party(record.sellers),
                meta=PREVIOUS_OWNER_META,
            )
        described = f"{record.deed_type or UNNAMED_DEED} {record.doc_no or ''}".strip()
        year = cls._year(deed)
        return JourneyEntryDTO(
            kind=JourneyEntryKind.OWNER.value,
            role=f"{ROOT_OF_TITLE_ROLE} · {year}" if year else ROOT_OF_TITLE_ROLE,
            badge=MOTHER_DEED_BADGE,
            party=cls.summarise_party(record.sellers),
            meta=EARLIEST_DEED_META.format(described=described),
        )

    @staticmethod
    def _reference(
        described: str, doc_no: Optional[str], consideration: Optional[str]
    ) -> str:
        parts = [described]
        if doc_no:
            parts.append(doc_no)
        if consideration:
            parts.append(consideration)
        return " · ".join(parts)

    @staticmethod
    def _year(deed: ChainDeedDTO) -> Optional[str]:
        record = deed.deed_record
        read = DeedDates.read(record.registration_date or record.execution_date)
        return str(read.year) if read is not None else None
