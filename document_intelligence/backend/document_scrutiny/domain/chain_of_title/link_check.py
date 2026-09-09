import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from document_scrutiny.constants.chain_constants import (
    EXTENT_TOLERANCE_FRACTION,
    NAME_CORROBORATION_FLOOR,
    NAME_STRONG_SCORE,
    NAME_WEAK_SCORE,
    LinkVerdict,
)
from document_scrutiny.domain.chain_of_title.deed_dates import DeedDates
from document_scrutiny.domain.chain_of_title.person_match import PersonMatch
from document_scrutiny.domain.chain_of_title.property_match import PropertyMatch
from document_scrutiny.dtos.chain_dtos import ChainDeedDTO, ChainLinkDTO, LinkChecksDTO

_WHITESPACE = re.compile(r"\s+")
UNNAMED_SELLER = "?"


class Identity(str):
    """How the current deed's seller relates to the deeds before it."""

    MATCH = "match"
    WEAK = "weak"
    NEW_ROOT = "new_root"


@dataclass(frozen=True)
class _Source:
    """The prior deed this seller most likely acquired the parcel from."""

    deed: ChainDeedDTO
    score: float
    corroborated: bool
    is_immediate_predecessor: bool


class LinkCheck:
    """Verifies that one deed's seller genuinely acquired what they are conveying.

    Carried from sale_deed_poc/build/poc/chain.py. Every deed before the current one is
    considered, not only the one immediately before it, because a seller may have built
    a holding up across several purchases from several people — and against only its
    predecessor that reads as a stranger selling land.
    """

    @classmethod
    def inspect(
        cls,
        previous: ChainDeedDTO,
        current: ChainDeedDTO,
        priors: Sequence[ChainDeedDTO],
    ) -> ChainLinkDTO:
        notes: List[str] = []
        source = cls._find_source(current=current, priors=priors, previous=previous)
        identity = cls._read_identity(source=source)
        cls._note_identity(
            notes=notes, identity=identity, source=source, current=current
        )

        cites_a_bundled_deed = cls._cites_any(current=current, priors=priors)
        property_agrees = PropertyMatch.same_property(
            source.deed.deed_record, current.deed_record
        )
        if property_agrees is False:
            notes.append(
                "Property identifiers (survey/plot) differ from the source deed."
            )

        extent_within_source = cls._check_extent(
            current=current, priors=priors, notes=notes
        )
        recital_cites_source = cls._check_recital(
            current=current, source=source, identity=identity, notes=notes
        )
        dates_in_order = cls._check_dates(
            previous=previous, current=current, notes=notes
        )

        checks = LinkChecksDTO(
            # A seller who matches nobody is only a problem if the deed nonetheless
            # claims one of these very deeds as its source of title.
            identity=identity != Identity.NEW_ROOT or not cites_a_bundled_deed,
            property_agrees=property_agrees is not False,
            extent_within_source=extent_within_source,
            recital_cites_source=recital_cites_source,
            dates_in_order=dates_in_order,
        )
        return ChainLinkDTO(
            from_document_id=previous.document_id,
            to_document_id=current.document_id,
            from_doc_no=previous.deed_record.doc_no,
            to_doc_no=current.deed_record.doc_no,
            verdict=cls._read_verdict(
                identity=identity,
                cites_a_bundled_deed=cites_a_bundled_deed,
                property_agrees=property_agrees,
                checks=checks,
                notes=notes,
                current=current,
                previous=previous,
            ),
            identity_score=round(source.score),
            checks=checks,
            notes=tuple(notes),
        )

    @classmethod
    def _find_source(
        cls,
        current: ChainDeedDTO,
        priors: Sequence[ChainDeedDTO],
        previous: ChainDeedDTO,
    ) -> _Source:
        """The prior deed whose buyer best matches this deed's seller, for this parcel.

        A prior purchase of a different survey or plot is skipped: title runs per
        parcel, so owning one field says nothing about selling another.
        """
        best: Optional[_Source] = None
        for prior in priors:
            if PropertyMatch.same_property(prior.deed_record, current.deed_record) is False:
                continue
            score, corroborated = PersonMatch.best(
                prior.deed_record.buyers, current.deed_record.sellers
            )
            if best is None or score > best.score:
                best = _Source(
                    deed=prior,
                    score=score,
                    corroborated=corroborated,
                    is_immediate_predecessor=prior.document_id == previous.document_id,
                )
        if best is None or best.score <= 0:
            return _Source(
                deed=best.deed if best is not None else previous,
                score=best.score if best is not None else 0.0,
                corroborated=False,
                is_immediate_predecessor=True,
            )
        return best

    @staticmethod
    def _read_identity(source: _Source) -> str:
        if source.score >= NAME_STRONG_SCORE:
            return Identity.MATCH
        if source.score >= NAME_WEAK_SCORE or (
            source.corroborated and source.score >= NAME_CORROBORATION_FLOOR
        ):
            return Identity.WEAK
        return Identity.NEW_ROOT

    @classmethod
    def _note_identity(
        cls,
        notes: List[str],
        identity: str,
        source: _Source,
        current: ChainDeedDTO,
    ) -> None:
        seller = cls._seller_name(current)
        if identity == Identity.MATCH:
            if not source.is_immediate_predecessor:
                notes.append(
                    f"Seller continues from {source.deed.deed_record.doc_no} (an "
                    f"earlier purchase, not the immediately previous deed)."
                )
            return
        if identity == Identity.WEAK:
            notes.append(
                f"Approximate name match ({source.score:.0f}/100) for seller "
                f"'{seller}' — verify this is the same person."
            )
            return
        notes.append(
            f"Seller '{seller}' is not a prior owner in this bundle — treated as a "
            f"new/original holding (normal when parcels are aggregated from multiple "
            f"sellers)."
        )

    @classmethod
    def _check_extent(
        cls,
        current: ChainDeedDTO,
        priors: Sequence[ChainDeedDTO],
        notes: List[str],
    ) -> Optional[bool]:
        """A seller may convey up to everything they bought, added together.

        Several purchases build one larger holding, so the ceiling is the sum, not any
        single deed. Exceeding it means the extra land has no source in this bundle.
        """
        conveyed = current.deed_record.property_info.extent_sq_yard
        acquired, anything_acquired = cls._total_acquired(current=current, priors=priors)
        if conveyed is None or not anything_acquired:
            return None
        if conveyed > acquired * (1 + EXTENT_TOLERANCE_FRACTION):
            notes.append(
                f"Conveys {conveyed:g} sq.yd but the seller acquired only "
                f"{acquired:g} sq.yd in total across all prior purchases — the extra "
                f"extent has no source deed in this bundle."
            )
            return False
        return True

    @staticmethod
    def _total_acquired(
        current: ChainDeedDTO, priors: Sequence[ChainDeedDTO]
    ) -> Tuple[float, bool]:
        total = 0.0
        anything = False
        for prior in priors:
            if PropertyMatch.same_property(prior.deed_record, current.deed_record) is False:
                continue
            score, _ = PersonMatch.best(
                prior.deed_record.buyers, current.deed_record.sellers
            )
            extent = prior.deed_record.property_info.extent_sq_yard
            if score >= NAME_WEAK_SCORE and extent:
                total += extent
                anything = True
        return total, anything

    @classmethod
    def _check_recital(
        cls,
        current: ChainDeedDTO,
        source: _Source,
        identity: str,
        notes: List[str],
    ) -> Optional[bool]:
        """A deed should name the deed its seller got the land under."""
        source_doc_no = cls._normalise(source.deed.deed_record.doc_no)
        if not source_doc_no or identity not in (Identity.MATCH, Identity.WEAK):
            return None
        cited = cls._cited_doc_numbers(current)
        if source_doc_no in cited:
            return True
        elsewhere = [
            reference
            for reference in current.deed_record.prior_deed_refs
            if cls._normalise(reference) != source_doc_no
        ]
        described = (
            f"; it cites {', '.join(elsewhere)} (not in bundle)." if elsewhere else "."
        )
        notes.append(
            f"{current.deed_record.doc_no or 'Deed'} does not cite "
            f"{source.deed.deed_record.doc_no} as its source of title{described}"
        )
        return False

    @classmethod
    def _check_dates(
        cls, previous: ChainDeedDTO, current: ChainDeedDTO, notes: List[str]
    ) -> Optional[bool]:
        previous_date = DeedDates.read(previous.deed_record.registration_date)
        current_date = DeedDates.read(current.deed_record.registration_date)
        if previous_date is None or current_date is None:
            return None
        if current_date >= previous_date:
            return True
        notes.append(
            f"{current.deed_record.doc_no} is dated before "
            f"{previous.deed_record.doc_no}."
        )
        return False

    @classmethod
    def _read_verdict(
        cls,
        identity: str,
        cites_a_bundled_deed: bool,
        property_agrees: Optional[bool],
        checks: LinkChecksDTO,
        notes: List[str],
        current: ChainDeedDTO,
        previous: ChainDeedDTO,
    ) -> str:
        if identity == Identity.NEW_ROOT and cites_a_bundled_deed:
            # The forgery shape: a stranger sells, yet the deed claims its title came
            # through one of the very deeds in this bundle.
            return LinkVerdict.BROKEN.value
        recital_failed = checks.recital_cites_source is False
        if (
            property_agrees is False
            or checks.extent_within_source is False
            or (recital_failed and cls._intermediate_missing(current, previous))
        ):
            return LinkVerdict.GAP.value
        if identity in (Identity.WEAK, Identity.NEW_ROOT) or notes:
            return LinkVerdict.WEAK.value
        return LinkVerdict.LINKED.value

    @classmethod
    def _intermediate_missing(
        cls, current: ChainDeedDTO, previous: ChainDeedDTO
    ) -> bool:
        """The deed cites a source that is not the previous deed and is not here at
        all, which is what a missing intermediate deed looks like."""
        cited = cls._cited_doc_numbers(current)
        return bool(cited) and cls._normalise(previous.deed_record.doc_no) not in cited

    @classmethod
    def _cites_any(
        cls, current: ChainDeedDTO, priors: Sequence[ChainDeedDTO]
    ) -> bool:
        cited = cls._cited_doc_numbers(current)
        return any(
            prior.deed_record.doc_no
            and cls._normalise(prior.deed_record.doc_no) in cited
            for prior in priors
        )

    @classmethod
    def _cited_doc_numbers(cls, current: ChainDeedDTO) -> set:
        return {
            cls._normalise(reference)
            for reference in current.deed_record.prior_deed_refs
        }

    @staticmethod
    def _normalise(doc_no: Optional[str]) -> str:
        return _WHITESPACE.sub("", str(doc_no or "")).lower()

    @staticmethod
    def _seller_name(current: ChainDeedDTO) -> str:
        sellers = current.deed_record.sellers
        return sellers[0].name if sellers else UNNAMED_SELLER
