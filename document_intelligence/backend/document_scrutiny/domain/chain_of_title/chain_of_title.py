import re
from typing import Dict, List, Sequence, Tuple

from document_scrutiny.constants.chain_constants import (
    ChainVerdict,
    LinkVerdict,
    TitleRole,
)
from document_scrutiny.domain.chain_of_title.chain_findings import ChainFindings
from document_scrutiny.domain.chain_of_title.deed_dates import DeedDates
from document_scrutiny.domain.chain_of_title.link_check import LinkCheck
from document_scrutiny.domain.chain_of_title.title_role import TitleRoleReader
from document_scrutiny.dtos.chain_dtos import (
    ChainDeedDTO,
    ChainLinkDTO,
    ChainOfTitleDTO,
)

_WHITESPACE = re.compile(r"\s+")


class ChainOfTitle:
    """Traces ownership through a set of registered deeds.

    Deterministic and explainable end to end: no model is consulted here. The deeds
    are put in date order and each consecutive transfer is asked whether the person
    selling had actually acquired what they are selling, and whether the paper says so.

    Carried from sale_deed_poc/build/poc/chain.py.
    """

    @classmethod
    def validate(cls, deeds: Sequence[ChainDeedDTO]) -> ChainOfTitleDTO:
        distinct, duplicates = cls._drop_duplicates(deeds=deeds)
        roles = cls._read_roles(deeds=distinct)
        conveyances = [
            deed for deed in distinct if roles[deed.document_id] == TitleRole.TITLE.value
        ]
        ordered = cls._order_by_date(conveyances)
        links = cls._build_links(ordered=ordered)
        counts = cls._count_verdicts(links=links)
        return ChainOfTitleDTO(
            ordered_document_ids=tuple(deed.document_id for deed in ordered),
            links=tuple(links),
            counts=counts,
            overall=cls._read_overall(counts=counts),
            findings=ChainFindings.build(links=links),
            roles_by_document_id=roles,
            duplicate_document_ids=tuple(deed.document_id for deed in duplicates),
        )

    @staticmethod
    def _read_roles(deeds: Sequence[ChainDeedDTO]) -> Dict[str, str]:
        """A power of attorney or an agreement to sell is set aside, not counted against
        the chain. Neither moves ownership, so neither can be a link in it."""
        return {
            deed.document_id: TitleRoleReader.read(
                deed_type=deed.deed_record.deed_type
            )
            for deed in deeds
        }

    @staticmethod
    def _drop_duplicates(
        deeds: Sequence[ChainDeedDTO],
    ) -> Tuple[List[ChainDeedDTO], List[ChainDeedDTO]]:
        """Collapses two copies of one registration number into the better-read one.

        A bundle photocopies the same deed twice often enough to matter, and the
        inventory pass is told to over-segment when unsure. Left alone, the duplicate
        becomes a transfer from a person to themselves.
        """
        kept: List[ChainDeedDTO] = []
        duplicates: List[ChainDeedDTO] = []
        best_by_doc_no: Dict[str, ChainDeedDTO] = {}
        for deed in deeds:
            doc_no = _WHITESPACE.sub("", str(deed.deed_record.doc_no or "")).lower()
            if not doc_no:
                # Nothing to match on. An unnumbered deed is kept: dropping a
                # transfer because it was badly read would invent a gap.
                kept.append(deed)
                continue
            held = best_by_doc_no.get(doc_no)
            if held is None:
                best_by_doc_no[doc_no] = deed
                kept.append(deed)
                continue
            if deed.read_confidence > held.read_confidence:
                kept[kept.index(held)] = deed
                best_by_doc_no[doc_no] = deed
                duplicates.append(held)
            else:
                duplicates.append(deed)
        return kept, duplicates

    @staticmethod
    def _order_by_date(deeds: Sequence[ChainDeedDTO]) -> List[ChainDeedDTO]:
        # Oldest first. A bundle arrives in whatever order it was photocopied, and the
        # chain only means anything in the order the transfers happened.
        return sorted(
            deeds,
            key=lambda deed: DeedDates.sort_key(deed.deed_record.registration_date),
        )

    @staticmethod
    def _build_links(ordered: Sequence[ChainDeedDTO]) -> List[ChainLinkDTO]:
        # Each transfer is checked against its immediate predecessor for the timeline,
        # and against every deed before it so an aggregated holding still resolves.
        return [
            LinkCheck.inspect(
                previous=ordered[index],
                current=ordered[index + 1],
                priors=ordered[: index + 1],
            )
            for index in range(len(ordered) - 1)
        ]

    @staticmethod
    def _count_verdicts(links: Sequence[ChainLinkDTO]) -> Dict[str, int]:
        counts = {verdict.value: 0 for verdict in LinkVerdict}
        for link in links:
            counts[link.verdict] = counts.get(link.verdict, 0) + 1
        return counts

    @staticmethod
    def _read_overall(counts: Dict[str, int]) -> str:
        if counts.get(LinkVerdict.BROKEN.value):
            return ChainVerdict.BROKEN.value
        if counts.get(LinkVerdict.GAP.value) or counts.get(LinkVerdict.WEAK.value):
            return ChainVerdict.REVIEW.value
        return ChainVerdict.INTACT.value
