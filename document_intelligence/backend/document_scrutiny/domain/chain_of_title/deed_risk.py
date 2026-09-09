from typing import Dict, List, Sequence, Set, Tuple

from document_scrutiny.constants.chain_constants import (
    SEVERITY_ORDER,
    FindingSeverity,
    LinkVerdict,
)
from document_scrutiny.constants.risk_constants import (
    AGREEMENT_ONLY_PHRASES,
    HIGH_RISK_FLOOR,
    MAXIMUM_RISK_SCORE,
    MEDIUM_RISK_FLOOR,
    POWER_OF_ATTORNEY_PHRASES,
    PRICE_DROP_FRACTION,
    RISK_SIGNAL_TITLES,
    SAME_PERSON_NAME_SCORE,
    WEIGHT_BY_SEVERITY,
    RiskLevel,
    RiskSignalCode,
)
from document_scrutiny.domain.chain_of_title.person_match import PersonMatch
from document_scrutiny.dtos.chain_dtos import ChainDeedDTO, ChainOfTitleDTO
from document_scrutiny.dtos.ownership_report_dtos import (
    RiskAssessmentDTO,
    RiskSignalDTO,
)

UNNUMBERED_DEED = "?"


class DeedRisk:
    """Gathers what a tired reviewer skims past, and says why each point was assigned.

    Deterministic and additive: no model, no hidden weighting. The score is a summary
    of the signals below it, never a substitute for reading them — which is why it is
    display only and moves no verdict.

    Carried from sale_deed_poc/build/poc/risk.py.
    """

    @classmethod
    def assess(
        cls, deeds: Sequence[ChainDeedDTO], chain: ChainOfTitleDTO
    ) -> RiskAssessmentDTO:
        signals: List[RiskSignalDTO] = []
        for deed in deeds:
            signals.extend(cls._read_one_deed(deed=deed))
        signals.extend(cls._read_identifiers_across_deeds(deeds=deeds))
        signals.extend(cls._read_chain(chain=chain))
        signals.extend(cls._read_prices(deeds=deeds, chain=chain))
        signals.sort(key=lambda signal: cls._position(signal.severity))
        score = cls._score(signals=signals)
        return RiskAssessmentDTO(
            score=score, level=cls._level(score=score), signals=tuple(signals)
        )

    @classmethod
    def _read_one_deed(cls, deed: ChainDeedDTO) -> List[RiskSignalDTO]:
        signals: List[RiskSignalDTO] = []
        record = deed.deed_record
        described = str(record.deed_type or "").lower()
        named = record.doc_no or UNNUMBERED_DEED

        if record.executed_via_gpa or cls._mentions(
            described, POWER_OF_ATTORNEY_PHRASES
        ):
            signals.append(
                cls._signal(
                    severity=FindingSeverity.HIGH.value,
                    code=RiskSignalCode.TITLE_VIA_GPA.value,
                    detail=(
                        f"Deed {named} passes title through a power of attorney — "
                        f"legally weak since the 2011 Suraj Lamp ruling."
                    ),
                )
            )
        if cls._mentions(described, AGREEMENT_ONLY_PHRASES):
            signals.append(
                cls._signal(
                    severity=FindingSeverity.HIGH.value,
                    code=RiskSignalCode.AGREEMENT_ONLY.value,
                    detail=(
                        f"Deed {named} is an agreement to sell — it does not by "
                        f"itself transfer ownership."
                    ),
                )
            )
        parties = tuple(record.sellers) + tuple(record.buyers)
        if parties and not any(party.pan or party.aadhaar for party in parties):
            signals.append(
                cls._signal(
                    severity=FindingSeverity.LOW.value,
                    code=RiskSignalCode.NO_PARTY_IDENTIFIER.value,
                    detail=(
                        f"Deed {named}: no PAN or government identifier for any "
                        f"party, so identity cannot be verified against a register."
                    ),
                )
            )
        return signals

    @classmethod
    def _read_identifiers_across_deeds(
        cls, deeds: Sequence[ChainDeedDTO]
    ) -> List[RiskSignalDTO]:
        """One PAN standing for two different people is the shape of an impersonation."""
        names_by_identifier = cls._collect_names_by_identifier(deeds=deeds)
        signals: List[RiskSignalDTO] = []
        for identifier, names in names_by_identifier.items():
            if not cls._names_disagree(names=names):
                continue
            listed = ", ".join(sorted(names))
            signals.append(
                cls._signal(
                    severity=FindingSeverity.MEDIUM.value,
                    code=RiskSignalCode.SAME_IDENTIFIER_DIFFERENT_NAMES.value,
                    detail=f"PAN {identifier} appears under differing names: {listed}.",
                )
            )
        return signals

    @staticmethod
    def _collect_names_by_identifier(
        deeds: Sequence[ChainDeedDTO],
    ) -> Dict[str, Set[str]]:
        names_by_identifier: Dict[str, Set[str]] = {}
        for deed in deeds:
            record = deed.deed_record
            for party in tuple(record.sellers) + tuple(record.buyers):
                if not party.pan:
                    continue
                names_by_identifier.setdefault(party.pan.upper(), set()).add(party.name)
        return names_by_identifier

    @staticmethod
    def _names_disagree(names: Set[str]) -> bool:
        if len(names) < 2:
            return False
        best = max(
            PersonMatch.score_names(name=left, comparison_name=right)
            for left in names
            for right in names
            if left != right
        )
        return best < SAME_PERSON_NAME_SCORE

    @classmethod
    def _read_chain(cls, chain: ChainOfTitleDTO) -> List[RiskSignalDTO]:
        signals: List[RiskSignalDTO] = []
        broken = chain.counts.get(LinkVerdict.BROKEN.value, 0)
        gap = chain.counts.get(LinkVerdict.GAP.value, 0)
        weak = chain.counts.get(LinkVerdict.WEAK.value, 0)
        if broken:
            signals.append(
                cls._signal(
                    severity=FindingSeverity.HIGH.value,
                    code=RiskSignalCode.BROKEN_CHAIN.value,
                    detail=(
                        f"{cls._count(broken, 'transfer')} have no continuity — the "
                        f"chain does not hold as provided."
                    ),
                )
            )
        if gap:
            signals.append(
                cls._signal(
                    severity=FindingSeverity.HIGH.value,
                    code=RiskSignalCode.MISSING_DEED.value,
                    detail=(
                        f"{cls._count(gap, 'transfer')} reference a deed that is not "
                        f"here, or convey more land than was acquired."
                    ),
                )
            )
        if weak:
            signals.append(
                cls._signal(
                    severity=FindingSeverity.MEDIUM.value,
                    code=RiskSignalCode.WEAK_LINK.value,
                    detail=(
                        f"{cls._count(weak, 'link')} rely on an approximate name match."
                    ),
                )
            )
        return signals

    @classmethod
    def _read_prices(
        cls, deeds: Sequence[ChainDeedDTO], chain: ChainOfTitleDTO
    ) -> List[RiskSignalDTO]:
        """A consideration should generally climb over the years, not fall away."""
        priced = cls._priced_in_order(deeds=deeds, chain=chain)
        signals: List[RiskSignalDTO] = []
        for (earlier_name, earlier), (later_name, later) in zip(priced, priced[1:]):
            if later >= earlier * PRICE_DROP_FRACTION:
                continue
            signals.append(
                cls._signal(
                    severity=FindingSeverity.MEDIUM.value,
                    code=RiskSignalCode.PRICE_DROP.value,
                    detail=(
                        f"Consideration fell from Rs {earlier:,.0f} ({earlier_name}) "
                        f"to Rs {later:,.0f} ({later_name}) — possible distress sale, "
                        f"benami arrangement or under-valuation."
                    ),
                )
            )
        return signals

    @staticmethod
    def _priced_in_order(
        deeds: Sequence[ChainDeedDTO], chain: ChainOfTitleDTO
    ) -> List[Tuple[str, float]]:
        by_document_id = {deed.document_id: deed for deed in deeds}
        ordered = [
            by_document_id[document_id]
            for document_id in chain.ordered_document_ids
            if document_id in by_document_id
        ] or list(deeds)
        return [
            (
                deed.deed_record.doc_no or UNNUMBERED_DEED,
                float(deed.deed_record.consideration_inr),
            )
            for deed in ordered
            if deed.deed_record.consideration_inr
        ]

    @staticmethod
    def _signal(severity: str, code: str, detail: str) -> RiskSignalDTO:
        return RiskSignalDTO(
            severity=severity,
            code=code,
            title=RISK_SIGNAL_TITLES.get(code, code),
            detail=detail,
        )

    @staticmethod
    def _mentions(described: str, phrases: Sequence[str]) -> bool:
        return any(phrase in described for phrase in phrases)

    @staticmethod
    def _count(count: int, noun: str) -> str:
        return f"{count} {noun}" if count == 1 else f"{count} {noun}s"

    @staticmethod
    def _score(signals: Sequence[RiskSignalDTO]) -> int:
        total = sum(
            WEIGHT_BY_SEVERITY.get(signal.severity, 0) for signal in signals
        )
        return min(MAXIMUM_RISK_SCORE, total)

    @staticmethod
    def _level(score: int) -> str:
        if score >= HIGH_RISK_FLOOR:
            return RiskLevel.HIGH.value
        if score >= MEDIUM_RISK_FLOOR:
            return RiskLevel.MEDIUM.value
        return RiskLevel.LOW.value

    @staticmethod
    def _position(severity: str) -> int:
        if severity in SEVERITY_ORDER:
            return SEVERITY_ORDER.index(severity)
        return len(SEVERITY_ORDER) + 1
