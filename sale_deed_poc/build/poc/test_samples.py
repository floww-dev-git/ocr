"""The synthetic bundles must prove what they claim.

`make_samples.py` renders each bundle to PDF *and* declares the verdict that bundle is engineered
to produce. These tests feed the same specs — as the records a perfect extraction would yield —
through the real chain engine, so a fixture can never drift from its own claim: if someone edits a
name or an extent, the bundle stops proving its scenario here rather than silently in a demo.

This isolates the deterministic half. A live run that disagrees with these expectations is an
EXTRACTION problem (Gemini misread the page), not a chain-logic problem.
"""
from __future__ import annotations

import pytest

from chain import validate_chain
from make_samples import BundleSpec, ScenarioKind, build_bundles
from schema import DeedRecord, LINK_BROKEN, LINK_GAP, LINK_LINKED, LINK_WEAK

BUNDLES: tuple[BundleSpec, ...] = build_bundles()
IDS: list[str] = [b.filename for b in BUNDLES]


def _records(bundle: BundleSpec) -> list[DeedRecord]:
    return [d.as_deed_record(chr(ord("A") + i), bundle.filename)
            for i, d in enumerate(bundle.deeds)]


@pytest.mark.parametrize("bundle", BUNDLES, ids=IDS)
def test_bundle_produces_its_declared_overall_verdict(bundle: BundleSpec) -> None:
    result = validate_chain(_records(bundle))
    assert result["overall"] == bundle.expected_overall


@pytest.mark.parametrize("bundle", BUNDLES, ids=IDS)
def test_bundle_produces_its_declared_link_verdicts(bundle: BundleSpec) -> None:
    result = validate_chain(_records(bundle))
    verdicts = tuple(link["verdict"] for link in result["links"])
    assert verdicts == bundle.expected_links


@pytest.mark.parametrize("bundle", BUNDLES, ids=IDS)
def test_deeds_are_ordered_oldest_first(bundle: BundleSpec) -> None:
    result = validate_chain(_records(bundle))
    assert result["ordered_deed_ids"] == ["A", "B", "C"]


def _bundle_for(kind: ScenarioKind) -> BundleSpec:
    matches = [b for b in BUNDLES if b.scenario == kind.value]
    assert len(matches) == 1, f"expected exactly one {kind.value} bundle, found {len(matches)}"
    return matches[0]


def test_clean_chain_raises_no_caveats() -> None:
    """A clean chain must be clean all the way down — no notes, no failed checks."""
    result = validate_chain(_records(_bundle_for(ScenarioKind.CLEAN)))
    for link in result["links"]:
        assert link["notes"] == []
        assert all(link["checks"].values())
        assert link["id_score"] == 100


def test_weak_link_is_a_caveat_not_a_break() -> None:
    """Transliteration variance must land in the review band — never 'broken'."""
    result = validate_chain(_records(_bundle_for(ScenarioKind.WEAK)))
    weak = result["links"][1]
    assert weak["verdict"] == LINK_WEAK
    assert LINK_WEAK in weak["verdict"] and weak["verdict"] != LINK_BROKEN
    # the name still had to be recognisably the same person, just not exactly
    assert 60 <= weak["id_score"] < 85
    assert weak["checks"]["identity"] is True


def test_gap_link_names_the_unsourced_extent() -> None:
    """The 'sells more than she owns' signal must fail the extent check and say by how much."""
    result = validate_chain(_records(_bundle_for(ScenarioKind.GAP)))
    gap = result["links"][1]
    assert gap["verdict"] == LINK_GAP
    assert gap["checks"]["extent"] is False
    assert gap["id_score"] == 100, "the seller IS the prior buyer — only the area is wrong"
    assert any("600" in note and "400" in note for note in gap["notes"])


def test_broken_link_is_a_stranger_claiming_an_in_bundle_source() -> None:
    """The forgery shape: no continuity of person, yet the deed cites this chain's own deed."""
    result = validate_chain(_records(_bundle_for(ScenarioKind.BROKEN)))
    broken = result["links"][1]
    assert broken["verdict"] == LINK_BROKEN
    assert broken["checks"]["identity"] is False
    assert broken["id_score"] < 60


def test_every_link_verdict_is_covered_by_the_fixtures() -> None:
    """The set as a whole must exercise all four link verdicts, or it is not a complete suite."""
    seen = {v for b in BUNDLES for v in b.expected_links}
    assert seen == {LINK_LINKED, LINK_WEAK, LINK_GAP, LINK_BROKEN}
