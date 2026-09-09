"""The chain engine, verified in isolation.

Every case here is carried from sale_deed_poc/build/poc/test_chain.py. They are the
scenarios the engine exists to tell apart, and they are the reason the 85/60/48 bands
and the aggregate extent rule are shaped the way they are.
"""
from typing import Optional, Sequence

from document_extraction.dtos.deed_record_dtos import (
    DeedRecordDTO,
    PartyDTO,
    PropertyInfoDTO,
)
from document_scrutiny.constants.chain_constants import (
    NAME_STRONG_SCORE,
    NAME_WEAK_SCORE,
    ChainVerdict,
    LinkVerdict,
)
from document_scrutiny.domain.chain_of_title.chain_of_title import ChainOfTitle
from document_scrutiny.dtos.chain_dtos import ChainDeedDTO

LINKED = LinkVerdict.LINKED.value
WEAK = LinkVerdict.WEAK.value
GAP = LinkVerdict.GAP.value
BROKEN = LinkVerdict.BROKEN.value


def party(
    name: str,
    relation: str = "s/o",
    relative_name: str = "X",
    address: str = "Kondapur",
) -> PartyDTO:
    return PartyDTO(
        name=name, relation=relation, relative_name=relative_name, address=address
    )


def deed(
    document_id: str,
    doc_no: str,
    registration_date: str,
    sellers: Sequence[PartyDTO],
    buyers: Sequence[PartyDTO],
    survey_no: Optional[str],
    extent_sq_yard: Optional[float],
    prior_deed_refs: Sequence[str],
    plot_no: Optional[str] = "42",
    deed_type: str = "Sale Deed",
) -> ChainDeedDTO:
    return ChainDeedDTO(
        document_id=document_id,
        filename="bundle.pdf",
        deed_record=DeedRecordDTO(
            doc_no=doc_no,
            registration_date=registration_date,
            deed_type=deed_type,
            sellers=tuple(sellers),
            buyers=tuple(buyers),
            property_info=PropertyInfoDTO(
                survey_no=survey_no, plot_no=plot_no, extent_sq_yard=extent_sq_yard
            ),
            prior_deed_refs=tuple(prior_deed_refs),
        ),
    )


def build_deeds() -> Sequence[ChainDeedDTO]:
    """A clean link, a transliteration-weak link, and a suspected missing deed."""
    a = deed(
        "A", "1234/1998", "1998-07-09",
        [party("Kondapur Developers")],
        [party("Venkata Rao", "s/o", "Narasimha Rao")],
        "127/A", 300, [],
    )
    b = deed(
        "B", "2451/2007", "2007-03-14",
        [party("Venkata Rao", "s/o", "Narasimha Rao")],
        [party("Lakshmi Devi", "w/o", "Ramesh Babu")],
        "127/A", 300, ["1234/1998"],
    )
    c = deed(
        "C", "7789/2015", "2015-09-02",
        [party("Laxmi Devi", "w/o", "Ramesh Babu")],
        [party("Imran Khan", "s/o", "Abdul Rahman")],
        "127/A", 200, ["2451/2007"],
    )
    d = deed(
        "D", "3456/2023", "2023-06-21",
        [party("Imran Khan", "s/o", "Abdul Rahman")],
        [party("Ananya Sharma", "w/o", "Karthik")],
        "127/A", 300, ["6620/2019"],
    )
    return [d, a, c, b]  # deliberately unordered — the engine must sort


class TestTracingAChainOfTitle:
    def test_the_deeds_are_put_in_the_order_the_transfers_happened(self):
        """A bundle arrives in whatever order it was photocopied."""
        # Act
        chain = ChainOfTitle.validate(deeds=build_deeds())

        # Assert
        assert chain.ordered_document_ids == ("A", "B", "C", "D")

    def test_a_transfer_where_everything_reconciles_is_reported_clean(self):
        # Act
        chain = ChainOfTitle.validate(deeds=build_deeds())

        # Assert
        assert chain.links[0].verdict == LINKED

    def test_a_transliterated_name_is_a_caveat_not_a_different_person(self):
        """'Lakshmi Devi' selling as 'Laxmi Devi' is one person spelled two ways."""
        # Act
        chain = ChainOfTitle.validate(deeds=build_deeds())

        # Assert
        assert chain.links[1].verdict == WEAK
        assert chain.links[1].checks.identity is True

    def test_selling_more_land_than_was_bought_reads_as_a_missing_deed(self):
        # Act
        chain = ChainOfTitle.validate(deeds=build_deeds())

        # Assert
        assert chain.links[2].verdict == GAP
        assert chain.links[2].checks.extent_within_source is False

    def test_the_chain_as_a_whole_needs_review(self):
        # Act
        chain = ChainOfTitle.validate(deeds=build_deeds())

        # Assert
        assert chain.overall == ChainVerdict.REVIEW.value
        assert chain.counts == {LINKED: 1, WEAK: 1, GAP: 1, BROKEN: 0}

    def test_a_chain_of_one_deed_has_no_links_to_check(self):
        # Act
        chain = ChainOfTitle.validate(deeds=[build_deeds()[1]])

        # Assert
        assert chain.links == ()
        assert chain.overall == ChainVerdict.INTACT.value

    def test_no_deeds_at_all_is_reported_rather_than_raising(self):
        # Act
        chain = ChainOfTitle.validate(deeds=[])

        # Assert
        assert chain.ordered_document_ids == ()
        assert chain.overall == ChainVerdict.INTACT.value


class TestWhenContinuityMustNotBeCalledBroken:
    def test_a_buyer_named_inside_a_multi_party_seller_still_carries_over(self):
        """The buyer's whole name sits inside the seller string, and the case differs."""
        # Arrange
        a = deed(
            "A", "1/2006", "2006-11-03",
            [party("Acme Holdings")],
            [party("Arun Prasad Menon")],
            "9", 200, [],
        )
        b = deed(
            "B", "2/2024", "2024-12-23",
            [party("ZENITH TRADERS PRIVATE LIMITED, ARUN PRASAD MENON")],
            [party("Delta Developers")],
            "9", 200, ["1/2006"],
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[a, b])

        # Assert
        assert chain.links[0].verdict != BROKEN
        assert chain.links[0].identity_score >= NAME_STRONG_SCORE

    def test_a_partial_name_match_is_never_slammed_as_broken(self):
        # Arrange
        a = deed(
            "A", "1/2000", "2000-01-01",
            [party("Owner")], [party("Ramesh Babu", "s/o", "Rao")], "9", 100, [],
        )
        b = deed(
            "B", "2/2010", "2010-01-01",
            [party("Ramish Babu", "s/o", "Rao")], [party("Buyer")], "9", 100, ["1/2000"],
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[a, b])

        # Assert
        assert chain.links[0].verdict != BROKEN

    def test_a_property_nobody_read_does_not_count_against_the_link(self):
        """Penalising a link for a survey number that was never captured would report a
        reading failure as a title defect."""
        # Arrange
        owner = party("Ravi Kumar", "s/o", "Rao")
        a = deed("A", "1/2000", "2000-01-01", [party("X")], [owner], None, None, [], plot_no=None)
        b = deed(
            "B", "2/2010", "2010-01-01", [owner], [party("Y")], None, None, ["1/2000"],
            plot_no=None,
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[a, b])

        # Assert
        assert chain.links[0].verdict != BROKEN
        assert chain.links[0].checks.property_agrees is True

    def test_land_gathered_from_several_sellers_may_be_sold_as_one_parcel(self):
        """Three purchases of 200 build a 600 holding, so conveying 600 is not an
        over-conveyance. Judging each purchase alone would report a phantom gap."""
        # Arrange
        buyer = party("Aggregator Holdings", "s/o", "Promoter")
        first = deed("A", "1/2000", "2000-01-01", [party("Seller One")], [buyer], "10", 200, [])
        second = deed("B", "2/2001", "2001-01-01", [party("Seller Two")], [buyer], "10", 200, [])
        third = deed("C", "3/2002", "2002-01-01", [party("Seller Three")], [buyer], "10", 200, [])
        combined = deed(
            "D", "4/2003", "2003-01-01", [buyer], [party("Final Buyer")], "10", 600,
            ["1/2000", "2/2001", "3/2002"],
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[combined, first, third, second])

        # Assert
        big_sale = chain.links[-1]
        assert big_sale.checks.extent_within_source is not False
        assert big_sale.verdict not in (GAP, BROKEN)
        assert big_sale.identity_score >= NAME_STRONG_SCORE


class TestWhenContinuityMustBeQuestioned:
    def test_owning_one_parcel_says_nothing_about_selling_another(self):
        """Title runs per parcel: the prior purchase was survey 10, this deed sells 99."""
        # Arrange
        owner = party("Common Owner", "s/o", "X")
        first = deed("A", "1/2000", "2000-01-01", [party("Seller One")], [owner], "10", 200, [])
        second = deed(
            "B", "2/2010", "2010-01-01", [owner], [party("Final Buyer")], "99", 200,
            ["1/2000"],
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[first, second])

        # Assert
        assert chain.links[0].verdict != LINKED

    def test_a_stranger_selling_while_claiming_this_chain_is_broken(self):
        """The forgery shape: no continuity of person, yet the deed cites a deed here."""
        # Arrange
        a = deed(
            "A", "1/2000", "2000-01-01",
            [party("Owner Zero")], [party("Alice", "d/o", "Bob")], "5", 100, [],
        )
        b = deed(
            "B", "2/2010", "2010-01-01",
            [party("Completely Different", "s/o", "Nobody", "Elsewhere")],
            [party("Carol")], "5", 100, ["1/2000"],
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[a, b])

        # Assert
        assert chain.links[0].verdict == BROKEN
        assert chain.links[0].checks.identity is False
        assert chain.links[0].identity_score < NAME_WEAK_SCORE
        assert chain.overall == ChainVerdict.BROKEN.value

    def test_a_stranger_claiming_nothing_is_a_new_holding_not_a_break(self):
        """Land aggregated from an unrelated seller is normal; only a false claim of
        continuity is not."""
        # Arrange
        a = deed(
            "A", "1/2000", "2000-01-01",
            [party("Owner Zero")], [party("Alice", "d/o", "Bob")], "5", 100, [],
        )
        b = deed(
            "B", "2/2010", "2010-01-01",
            [party("Completely Different", "s/o", "Nobody", "Elsewhere")],
            [party("Carol")], "5", 100, [],
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[a, b])

        # Assert
        assert chain.links[0].verdict == WEAK
        assert chain.links[0].checks.identity is True

    def test_a_deed_dated_before_the_one_it_follows_is_reported(self):
        # Arrange
        owner = party("Owner One", "s/o", "Rao")
        a = deed("A", "1/2010", "2010-05-05", [party("X")], [owner], "7", 100, [])
        b = deed("B", "2/2009", "2009-05-05", [owner], [party("Y")], "7", 100, ["1/2010"])

        # Act — B sorts first by date, so the engine checks A against B
        chain = ChainOfTitle.validate(deeds=[a, b])

        # Assert
        assert chain.ordered_document_ids == ("B", "A")


class TestSettingAsideDocumentsThatConveyNothing:
    def test_an_agreement_to_sell_is_not_a_link_in_the_chain(self):
        """It promises a transfer; it does not make one. Counting it would invent a
        break between two deeds that in fact follow each other."""
        # Arrange
        owner = party("Ravi Kumar", "s/o", "Rao")
        a = deed("A", "1/2000", "2000-01-01", [party("X")], [owner], "7", 100, [])
        agreement = deed(
            "B", "2/2005", "2005-01-01", [owner], [party("Hopeful Buyer")], "7", 100,
            ["1/2000"], deed_type="Agreement to Sell",
        )
        c = deed("C", "3/2010", "2010-01-01", [owner], [party("Real Buyer")], "7", 100, ["1/2000"])

        # Act
        chain = ChainOfTitle.validate(deeds=[a, agreement, c])

        # Assert
        assert chain.excluded_document_ids == ("B",)
        assert chain.ordered_document_ids == ("A", "C")

    def test_a_power_of_attorney_is_set_aside_too(self):
        # Arrange
        owner = party("Ravi Kumar", "s/o", "Rao")
        a = deed("A", "1/2000", "2000-01-01", [party("X")], [owner], "7", 100, [])
        gpa = deed(
            "B", "2/2005", "2005-01-01", [owner], [party("Agent")], "7", 100, [],
            deed_type="General Power of Attorney",
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[a, gpa])

        # Assert
        assert chain.excluded_document_ids == ("B",)
        assert chain.links == ()

    def test_a_registration_summary_sheet_is_not_a_deed(self):
        # Arrange
        summary = deed(
            "S", "", "2020-01-01", [], [], "7", None, [],
            deed_type="Registration Summary",
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[summary])

        # Assert
        assert chain.excluded_document_ids == ("S",)

    def test_a_sale_deed_is_kept_even_when_its_type_mentions_an_agreement(self):
        """A genuine "Sale Deed cum ..." still conveys."""
        # Arrange
        owner = party("Ravi Kumar", "s/o", "Rao")
        a = deed("A", "1/2000", "2000-01-01", [party("X")], [owner], "7", 100, [])
        b = deed(
            "B", "2/2010", "2010-01-01", [owner], [party("Y")], "7", 100, ["1/2000"],
            deed_type="Sale Deed cum Development Agreement",
        )

        # Act
        chain = ChainOfTitle.validate(deeds=[a, b])

        # Assert
        assert chain.excluded_document_ids == ()
        assert chain.ordered_document_ids == ("A", "B")


class TestWhatTheOfficerIsGivenToRead:
    def test_the_worst_finding_is_put_first(self):
        # Act
        chain = ChainOfTitle.validate(deeds=build_deeds())

        # Assert
        assert [finding.severity for finding in chain.findings] == [
            "high",
            "medium",
            "clear",
        ]

    def test_a_finding_names_the_two_deeds_it_is_about(self):
        # Act
        chain = ChainOfTitle.validate(deeds=build_deeds())

        # Assert
        assert any(
            "7789/2015" in finding.title and "3456/2023" in finding.title
            for finding in chain.findings
        )

    def test_a_clean_link_still_says_that_it_was_examined(self):
        """An absence of comment is not the same as a link that held."""
        # Act
        chain = ChainOfTitle.validate(deeds=build_deeds())
        clean = next(finding for finding in chain.findings if finding.verdict == LINKED)

        # Assert
        assert clean.detail == "Identity, property, recital and dates reconcile cleanly."

    def test_the_unsourced_extent_is_quantified_not_merely_flagged(self):
        # Act
        chain = ChainOfTitle.validate(deeds=build_deeds())
        gap = next(finding for finding in chain.findings if finding.verdict == GAP)

        # Assert
        assert "300" in gap.detail and "200" in gap.detail
