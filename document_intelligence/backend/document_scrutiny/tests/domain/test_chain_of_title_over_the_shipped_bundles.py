"""The shipped bundles must prove what they claim.

Each bundle spec declares the verdict it is engineered to produce. These tests feed
the same specs — as the records a perfect read would yield — through the real chain
engine, so a fixture can never drift from its own claim: edit a name or an extent and
the bundle stops proving its scenario here, rather than silently in a demo.

This isolates the deterministic half. A live run that disagrees with these
expectations is an extraction problem, not a chain-logic problem.

Carried from sale_deed_poc/build/poc/test_samples.py.
"""
from typing import List

import pytest

from document_extraction.adapters.bundle_sample_reads import (
    BROKEN_STRANGER_SELLER_FILENAME,
    BUNDLE_SPECS,
    CLEAN_CHAIN_FILENAME,
    GAP_EXTENT_OVERFLOW_FILENAME,
    PAGES_PER_DEED,
    WEAK_TRANSLITERATION_FILENAME,
    BundleSpec,
)
from document_scrutiny.constants.chain_constants import (
    NAME_STRONG_SCORE,
    NAME_WEAK_SCORE,
    ChainVerdict,
    LinkVerdict,
)
from document_scrutiny.domain.chain_of_title.chain_of_title import ChainOfTitle
from document_scrutiny.dtos.chain_dtos import ChainDeedDTO

PERFECT_IDENTITY_SCORE = 100
BUNDLE_IDS = [spec.filename for spec in BUNDLE_SPECS]


def as_chain_deeds(bundle: BundleSpec) -> List[ChainDeedDTO]:
    """The bundle's deeds as the chain would receive them after segmentation."""
    return [
        ChainDeedDTO(
            document_id=f"document_{index}",
            filename=bundle.filename,
            deed_record=deed.as_deed_record(),
            page_start=index * PAGES_PER_DEED,
            page_end=index * PAGES_PER_DEED + PAGES_PER_DEED - 1,
        )
        for index, deed in enumerate(bundle.deeds)
    ]


def bundle_named(filename: str) -> BundleSpec:
    return next(spec for spec in BUNDLE_SPECS if spec.filename == filename)


def chain_for(filename: str):
    return ChainOfTitle.validate(deeds=as_chain_deeds(bundle_named(filename)))


class TestEveryBundleProvesItsOwnClaim:
    @pytest.mark.parametrize("bundle", BUNDLE_SPECS, ids=BUNDLE_IDS)
    def test_the_declared_overall_verdict_is_what_the_engine_returns(
        self, bundle: BundleSpec
    ):
        # Act
        chain = ChainOfTitle.validate(deeds=as_chain_deeds(bundle))

        # Assert
        assert chain.overall == bundle.expected_overall

    @pytest.mark.parametrize("bundle", BUNDLE_SPECS, ids=BUNDLE_IDS)
    def test_the_declared_link_verdicts_are_what_the_engine_returns(
        self, bundle: BundleSpec
    ):
        # Act
        chain = ChainOfTitle.validate(deeds=as_chain_deeds(bundle))

        # Assert
        assert tuple(link.verdict for link in chain.links) == bundle.expected_links

    @pytest.mark.parametrize("bundle", BUNDLE_SPECS, ids=BUNDLE_IDS)
    def test_the_deeds_are_read_oldest_first(self, bundle: BundleSpec):
        # Act
        chain = ChainOfTitle.validate(deeds=as_chain_deeds(bundle))

        # Assert
        assert chain.ordered_document_ids == (
            "document_0",
            "document_1",
            "document_2",
        )

    @pytest.mark.parametrize("bundle", BUNDLE_SPECS, ids=BUNDLE_IDS)
    def test_no_deed_in_a_title_bundle_is_set_aside(self, bundle: BundleSpec):
        # Act
        chain = ChainOfTitle.validate(deeds=as_chain_deeds(bundle))

        # Assert
        assert chain.excluded_document_ids == ()

    def test_the_declared_vocabulary_is_the_engines_own(self):
        """The fixtures restate the verdict strings rather than import them, because
        this dependency only runs one way. This is what keeps the two in step."""
        # Arrange
        link_verdicts = {verdict.value for verdict in LinkVerdict}
        chain_verdicts = {verdict.value for verdict in ChainVerdict}

        # Assert
        for bundle in BUNDLE_SPECS:
            assert bundle.expected_overall in chain_verdicts
            assert set(bundle.expected_links) <= link_verdicts

    def test_the_four_bundles_between_them_exercise_every_link_verdict(self):
        """Anything less is not a complete suite."""
        # Arrange
        declared = {
            verdict for bundle in BUNDLE_SPECS for verdict in bundle.expected_links
        }

        # Assert
        assert declared == {verdict.value for verdict in LinkVerdict}


class TestWhatEachBundleShows:
    def test_a_clean_chain_is_clean_all_the_way_down(self):
        """No notes, no failed checks, and every seller exactly the previous buyer."""
        # Act
        chain = chain_for(CLEAN_CHAIN_FILENAME)

        # Assert
        for link in chain.links:
            assert link.notes == ()
            assert link.checks.all_agree()
            assert link.identity_score == PERFECT_IDENTITY_SCORE

    def test_a_transliterated_seller_lands_in_the_review_band(self):
        """'Lakshmi Narayanan' conveying as 'Laxmi Narayan' is a caveat for a human,
        never a break — but the name still had to be recognisably the same person."""
        # Act
        weak = chain_for(WEAK_TRANSLITERATION_FILENAME).links[1]

        # Assert
        assert weak.verdict == LinkVerdict.WEAK.value
        assert NAME_WEAK_SCORE <= weak.identity_score < NAME_STRONG_SCORE
        assert weak.checks.identity is True
        assert any("verify this is the same person" in note for note in weak.notes)

    def test_selling_more_land_than_was_bought_names_the_unsourced_extent(self):
        # Act
        gap = chain_for(GAP_EXTENT_OVERFLOW_FILENAME).links[1]

        # Assert
        assert gap.verdict == LinkVerdict.GAP.value
        assert gap.checks.extent_within_source is False
        # The seller IS the prior buyer; only the area is wrong.
        assert gap.identity_score == PERFECT_IDENTITY_SCORE
        assert any("600" in note and "400" in note for note in gap.notes)

    def test_a_stranger_selling_while_citing_this_chain_is_broken(self):
        # Act
        broken = chain_for(BROKEN_STRANGER_SELLER_FILENAME).links[1]

        # Assert
        assert broken.verdict == LinkVerdict.BROKEN.value
        assert broken.checks.identity is False
        assert broken.identity_score < NAME_WEAK_SCORE

    def test_the_broken_bundle_puts_the_break_in_front_of_the_officer_first(self):
        # Act
        chain = chain_for(BROKEN_STRANGER_SELLER_FILENAME)

        # Assert
        assert chain.findings[0].severity == "high"
        assert "Broken link" in chain.findings[0].title
        assert "5820/2019" in chain.findings[0].title

    def test_the_clean_bundle_still_reports_that_each_link_was_examined(self):
        # Act
        chain = chain_for(CLEAN_CHAIN_FILENAME)

        # Assert
        assert len(chain.findings) == 2
        assert {finding.severity for finding in chain.findings} == {"clear"}
