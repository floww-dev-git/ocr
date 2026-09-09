from typing import Dict, List, Optional, Sequence, Tuple

from document_scrutiny.constants.chain_constants import LinkVerdict, TitleRole
from document_scrutiny.constants.report_constants import (
    ATTENTION_ACTIONS,
    ATTENTION_SEVERITIES,
    ATTENTION_VERBS,
    BROKEN_HEADLINE,
    BROKEN_PLAIN,
    CLEAN_HEADLINE,
    CLEAN_PLAIN,
    DEFAULT_ATTENTION_ACTION,
    GAP_REASON,
    MANY_THINGS,
    MANY_THINGS_VERB,
    NOTHING_TO_TRACE_HEADLINE,
    NOTHING_TO_TRACE_PLAIN,
    ONE_THING,
    ONE_THING_VERB,
    REVIEW_HEADLINE,
    REVIEW_PLAIN,
    SINGLE_DEED_HEADLINE,
    SINGLE_DEED_PLAIN,
    THE_ROOT_DEED,
    WEAK_REASON,
    ReportVerdictLevel,
)
from document_scrutiny.domain.chain_of_title.deed_dates import DeedDates
from document_scrutiny.domain.chain_of_title.deed_risk import DeedRisk
from document_scrutiny.domain.chain_of_title.ownership_journey import OwnershipJourney
from document_scrutiny.dtos.chain_dtos import ChainDeedDTO, ChainOfTitleDTO
from document_scrutiny.dtos.ownership_report_dtos import (
    AttentionItemDTO,
    AuthorityDocumentDTO,
    DocumentRoleRowDTO,
    OwnershipReportDTO,
    PropertySummaryDTO,
    ReportStatsDTO,
    ReportVerdictDTO,
)

PROPERTY_FIELDS = ("survey_no", "plot_no", "extent_text", "locality", "boundaries")


class OwnershipReport:
    """What the officer reads: who owns this land, how they got it, and what to chase.

    Assembly only — every judgement here was already made by the chain engine or the
    risk assessor. This decides what to say about it, in words rather than verdict codes.

    Carried from sale_deed_poc/build/poc/report.py::build_report_v2.
    """

    @classmethod
    def compose(
        cls,
        thread_id: str,
        deeds: Sequence[ChainDeedDTO],
        chain: ChainOfTitleDTO,
    ) -> OwnershipReportDTO:
        by_role = cls._group_by_role(deeds=deeds, chain=chain)
        title = by_role[TitleRole.TITLE.value]
        authority = by_role[TitleRole.AUTHORITY.value]
        ordered = cls._in_chain_order(title=title, chain=chain)
        return OwnershipReportDTO(
            thread_id=thread_id,
            verdict=cls._read_verdict(title=title, chain=chain, ordered=ordered),
            stats=cls._build_stats(title=title, chain=chain, ordered=ordered),
            property_summary=cls._summarise_property(
                deeds=title or list(deeds)
            ),
            journey=tuple(
                OwnershipJourney.compose(
                    ordered=ordered, links=chain.links, authority=authority
                )
            ),
            authority=cls._describe_authority(authority=authority),
            documents_by_role=cls._build_role_rows(by_role=by_role, ordered=ordered),
            attention=cls._build_attention(chain=chain),
            risk=DeedRisk.assess(deeds=deeds, chain=chain),
            chain=chain,
        )

    @staticmethod
    def _group_by_role(
        deeds: Sequence[ChainDeedDTO], chain: ChainOfTitleDTO
    ) -> Dict[str, List[ChainDeedDTO]]:
        grouped: Dict[str, List[ChainDeedDTO]] = {
            role.value: [] for role in TitleRole
        }
        duplicates = set(chain.duplicate_document_ids)
        for deed in deeds:
            if deed.document_id in duplicates:
                continue
            role = chain.roles_by_document_id.get(
                deed.document_id, TitleRole.TITLE.value
            )
            grouped[role].append(deed)
        return grouped

    @staticmethod
    def _in_chain_order(
        title: Sequence[ChainDeedDTO], chain: ChainOfTitleDTO
    ) -> List[ChainDeedDTO]:
        by_document_id = {deed.document_id: deed for deed in title}
        return [
            by_document_id[document_id]
            for document_id in chain.ordered_document_ids
            if document_id in by_document_id
        ]

    @classmethod
    def _read_verdict(
        cls,
        title: Sequence[ChainDeedDTO],
        chain: ChainOfTitleDTO,
        ordered: Sequence[ChainDeedDTO],
    ) -> ReportVerdictDTO:
        if not title:
            return ReportVerdictDTO(
                level=ReportVerdictLevel.REVIEW.value,
                headline=NOTHING_TO_TRACE_HEADLINE,
                plain=NOTHING_TO_TRACE_PLAIN,
            )
        breaks = chain.counts.get(LinkVerdict.BROKEN.value, 0)
        need_review = chain.counts.get(LinkVerdict.WEAK.value, 0) + chain.counts.get(
            LinkVerdict.GAP.value, 0
        )
        if breaks:
            return ReportVerdictDTO(
                level=ReportVerdictLevel.BROKEN.value,
                headline=BROKEN_HEADLINE,
                plain=BROKEN_PLAIN.format(count=len(title)),
            )
        if len(title) < 2:
            # One deed cannot be traced anywhere. Calling that clean would present an
            # absence of evidence as evidence.
            return ReportVerdictDTO(
                level=ReportVerdictLevel.REVIEW.value,
                headline=SINGLE_DEED_HEADLINE,
                plain=SINGLE_DEED_PLAIN,
            )
        root_year = cls._year(ordered[0]) if ordered else None
        if need_review:
            return ReportVerdictDTO(
                level=ReportVerdictLevel.REVIEW.value,
                headline=REVIEW_HEADLINE.format(
                    root=root_year or THE_ROOT_DEED,
                    count=need_review,
                    things=ONE_THING if need_review == 1 else MANY_THINGS,
                    verb=ONE_THING_VERB if need_review == 1 else MANY_THINGS_VERB,
                ),
                plain=REVIEW_PLAIN.format(
                    count=len(title), reasons=cls._describe_reasons(chain=chain)
                ),
            )
        return ReportVerdictDTO(
            level=ReportVerdictLevel.CLEAN.value,
            headline=CLEAN_HEADLINE.format(root=root_year or THE_ROOT_DEED),
            plain=CLEAN_PLAIN.format(count=len(title)),
        )

    @staticmethod
    def _describe_reasons(chain: ChainOfTitleDTO) -> str:
        reasons = []
        if chain.counts.get(LinkVerdict.GAP.value):
            reasons.append(GAP_REASON)
        if chain.counts.get(LinkVerdict.WEAK.value):
            reasons.append(WEAK_REASON)
        return " and ".join(reasons)

    @classmethod
    def _build_stats(
        cls,
        title: Sequence[ChainDeedDTO],
        chain: ChainOfTitleDTO,
        ordered: Sequence[ChainDeedDTO],
    ) -> ReportStatsDTO:
        return ReportStatsDTO(
            title_deed_count=len(title),
            span_from=cls._year(ordered[0]) if ordered else None,
            span_to=cls._year(ordered[-1]) if ordered else None,
            need_review=chain.counts.get(LinkVerdict.WEAK.value, 0)
            + chain.counts.get(LinkVerdict.GAP.value, 0),
            breaks=chain.counts.get(LinkVerdict.BROKEN.value, 0),
        )

    @staticmethod
    def _summarise_property(deeds: Sequence[ChainDeedDTO]) -> PropertySummaryDTO:
        """The fullest description any deed gave, with a later deed winning.

        A photocopied 1987 deed often names only a survey number, while the deed being
        relied on carries the whole schedule.
        """
        found: Dict[str, Optional[str]] = {name: None for name in PROPERTY_FIELDS}
        for deed in deeds:
            property_info = deed.deed_record.property_info
            for name in PROPERTY_FIELDS:
                value = getattr(property_info, name, None)
                if value:
                    found[name] = value
        return PropertySummaryDTO(**found)

    @classmethod
    def _describe_authority(
        cls, authority: Sequence[ChainDeedDTO]
    ) -> Tuple[AuthorityDocumentDTO, ...]:
        return tuple(
            AuthorityDocumentDTO(
                document_id=deed.document_id,
                deed_type=deed.deed_record.deed_type,
                doc_no=deed.deed_record.doc_no,
                owner=OwnershipJourney.summarise_party(deed.deed_record.sellers).name,
                holder=OwnershipJourney.summarise_party(deed.deed_record.buyers).name,
            )
            for deed in authority
        )

    @classmethod
    def _build_role_rows(
        cls,
        by_role: Dict[str, List[ChainDeedDTO]],
        ordered: Sequence[ChainDeedDTO],
    ) -> Dict[str, Tuple[DocumentRoleRowDTO, ...]]:
        root_document_id = ordered[0].document_id if ordered else None
        return {
            role: tuple(
                DocumentRoleRowDTO(
                    document_id=deed.document_id,
                    deed_type=deed.deed_record.deed_type,
                    doc_no=deed.deed_record.doc_no,
                    date=deed.deed_record.registration_date
                    or deed.deed_record.execution_date,
                    is_root=deed.document_id == root_document_id,
                )
                for deed in deeds
            )
            for role, deeds in by_role.items()
        }

    @staticmethod
    def _build_attention(chain: ChainOfTitleDTO) -> Tuple[AttentionItemDTO, ...]:
        """Only what the officer has to do something about; a verified link is not a task."""
        return tuple(
            AttentionItemDTO(
                severity=ATTENTION_SEVERITIES[finding.verdict],
                verb=ATTENTION_VERBS[finding.verdict],
                title=finding.title,
                detail=finding.detail,
                action=ATTENTION_ACTIONS.get(
                    finding.verdict, DEFAULT_ATTENTION_ACTION
                ),
            )
            for finding in chain.findings
            if finding.verdict in ATTENTION_VERBS
        )

    @staticmethod
    def _year(deed: ChainDeedDTO) -> Optional[str]:
        record = deed.deed_record
        read = DeedDates.read(record.registration_date or record.execution_date)
        return str(read.year) if read is not None else None
