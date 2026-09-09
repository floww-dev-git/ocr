"""Tests for the deterministic chain engine — the core IP, verified in isolation.

Reproduces the sample scenario: a clean link, a transliteration-weak link, and a
suspected-missing-deed gap.
"""
from schema import DeedRecord, Party, PropertyInfo, LINK_LINKED, LINK_WEAK, LINK_GAP, LINK_BROKEN, OVERALL_REVIEW
from chain import validate_chain


def _deed(deed_id, doc_no, date, sellers, buyers, survey, extent, refs):
    return DeedRecord(
        deed_id=deed_id, doc_no=doc_no, registration_date=date, deed_type="Sale Deed",
        sellers=sellers, buyers=buyers,
        property=PropertyInfo(survey_no=survey, plot_no="42", extent_sqyd=extent),
        prior_deed_refs=refs, confidence=0.9,
    )


def _p(name, rel="s/o", rel_name="X", addr="Kondapur"):
    return Party(name=name, relation=rel, relative_name=rel_name, address=addr)


def build_deeds():
    a = _deed("A", "1234/1998", "1998-07-09", [_p("Kondapur Developers")], [_p("Venkata Rao", "s/o", "Narasimha Rao")], "127/A", 300, [])
    b = _deed("B", "2451/2007", "2007-03-14", [_p("Venkata Rao", "s/o", "Narasimha Rao")], [_p("Lakshmi Devi", "w/o", "Ramesh Babu")], "127/A", 300, ["1234/1998"])
    c = _deed("C", "7789/2015", "2015-09-02", [_p("Laxmi Devi", "w/o", "Ramesh Babu")], [_p("Imran Khan", "s/o", "Abdul Rahman")], "127/A", 200, ["2451/2007"])
    d = _deed("D", "3456/2023", "2023-06-21", [_p("Imran Khan", "s/o", "Abdul Rahman")], [_p("Ananya Sharma", "w/o", "Karthik")], "127/A", 300, ["6620/2019"])
    return [d, a, c, b]  # deliberately unordered → engine must sort


def test_orders_by_date():
    r = validate_chain(build_deeds())
    assert r["ordered_deed_ids"] == ["A", "B", "C", "D"]


def test_clean_link_A_to_B():
    r = validate_chain(build_deeds())
    link = r["links"][0]  # A→B
    assert link["verdict"] == LINK_LINKED


def test_weak_link_B_to_C_transliteration():
    r = validate_chain(build_deeds())
    link = r["links"][1]  # B→C : Lakshmi vs Laxmi
    assert link["verdict"] == LINK_WEAK
    assert link["checks"]["identity"] is True  # resolved via relative/address


def test_gap_link_C_to_D_extent():
    r = validate_chain(build_deeds())
    link = r["links"][2]  # C→D : sells 300 but acquired 200, cites unknown deed
    assert link["verdict"] == LINK_GAP
    assert link["checks"]["extent"] is False


def test_overall_review():
    r = validate_chain(build_deeds())
    assert r["overall"] == OVERALL_REVIEW
    assert r["counts"][LINK_LINKED] == 1
    assert r["counts"][LINK_WEAK] == 1
    assert r["counts"][LINK_GAP] == 1
    assert r["counts"][LINK_BROKEN] == 0


def test_name_overlap_in_multiparty_seller_is_not_broken():
    # buyer's full name is CONTAINED in a multi-party seller string, and case differs → owner carries over.
    # (mock names; demonstrates the containment + case-insensitive match)
    a = _deed("A", "1/2006", "2006-11-03", [_p("Acme Holdings")], [_p("Arun Prasad Menon", "s/o", "X")], "9", 200, [])
    b = _deed("B", "2/2024", "2024-12-23",
              [_p("ZENITH TRADERS PRIVATE LIMITED, ARUN PRASAD MENON", "s/o", "X")],
              [_p("Delta Developers")], "9", 200, ["1/2006"])
    r = validate_chain([a, b])
    assert r["links"][0]["verdict"] != LINK_BROKEN
    assert r["links"][0]["id_score"] >= 85


def test_partial_name_match_is_not_broken():
    # a transliteration/partial match must not be slammed as BROKEN
    a = _deed("A", "1/2000", "2000-01-01", [_p("Owner")], [_p("Ramesh Babu", "s/o", "Rao")], "9", 100, [])
    b = _deed("B", "2/2010", "2010-01-01", [_p("Ramish Babu", "s/o", "Rao")], [_p("Buyer")], "9", 100, ["1/2000"])
    r = validate_chain([a, b])
    assert r["links"][0]["verdict"] != LINK_BROKEN


def test_unknown_property_does_not_break_link():
    # survey/plot not extracted on either deed → must NOT force a 'broken' on property grounds
    from schema import DeedRecord, PropertyInfo, Party
    a = DeedRecord(deed_id="A", doc_no="1/2000", registration_date="2000-01-01", deed_type="Sale Deed",
                   sellers=[Party(name="X")], buyers=[Party(name="Ravi Kumar", relation="s/o", relative_name="Rao")],
                   property=PropertyInfo(), prior_deed_refs=[], confidence=0.9)
    b = DeedRecord(deed_id="B", doc_no="2/2010", registration_date="2010-01-01", deed_type="Sale Deed",
                   sellers=[Party(name="Ravi Kumar", relation="s/o", relative_name="Rao")], buyers=[Party(name="Y")],
                   property=PropertyInfo(), prior_deed_refs=["1/2000"], confidence=0.9)
    r = validate_chain([a, b])
    assert r["links"][0]["verdict"] != LINK_BROKEN


def test_aggregation_from_multiple_sellers_is_not_over_conveyance():
    # one buyer acquires 3 parcels (200 each) from 3 different sellers, then sells the combined 600.
    # the big sale must NOT be flagged as 'sells more than acquired' — extent aggregates.
    buyer = lambda: _p("Aggregator Holdings", "s/o", "Promoter")
    d1 = _deed("A", "1/2000", "2000-01-01", [_p("Seller One")], [buyer()], "10", 200, [])
    d2 = _deed("B", "2/2001", "2001-01-01", [_p("Seller Two")], [buyer()], "10", 200, [])
    d3 = _deed("C", "3/2002", "2002-01-01", [_p("Seller Three")], [buyer()], "10", 200, [])
    d4 = _deed("D", "4/2003", "2003-01-01", [buyer()], [_p("Final Buyer")], "10", 600, ["1/2000", "2/2001", "3/2002"])
    r = validate_chain([d4, d1, d3, d2])  # unordered on purpose
    big = r["links"][-1]                   # the combined sale (D3 -> D4)
    assert big["checks"].get("extent") is not False   # 600 <= 200+200+200, so NOT over-conveyance
    assert big["verdict"] not in (LINK_GAP, LINK_BROKEN)
    assert big["id_score"] >= 85                       # seller traces to prior acquisitions


def test_same_person_different_parcel_is_not_a_clean_carryover():
    # the same person acquired survey 10, but this deed sells survey 99 — the prior purchase
    # is for a DIFFERENT parcel, so it must not count as a clean carry-over for survey 99.
    owner = lambda: _p("Common Owner", "s/o", "X")
    d1 = _deed("A", "1/2000", "2000-01-01", [_p("Seller One")], [owner()], "10", 200, [])
    d2 = _deed("B", "2/2010", "2010-01-01", [owner()], [_p("Final Buyer")], "99", 200, ["1/2000"])
    r = validate_chain([d1, d2])
    assert r["links"][0]["verdict"] != LINK_LINKED   # flagged, not treated as clean continuity


def test_broken_link_identity_mismatch():
    a = _deed("A", "1/2000", "2000-01-01", [_p("Owner Zero")], [_p("Alice", "d/o", "Bob")], "5", 100, [])
    b = _deed("B", "2/2010", "2010-01-01", [_p("Completely Different", "s/o", "Nobody", "Elsewhere")], [_p("Carol")], "5", 100, ["1/2000"])
    r = validate_chain([a, b])
    assert r["links"][0]["verdict"] == LINK_BROKEN
