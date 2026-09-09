"""The ownership report over the shipped bundles.

Carried from sale_deed_poc/build/poc/report.py::build_report_v2. The report makes no
new judgements — it says, in words, what the chain engine and the risk assessor already
found — so these tests are about what the officer is told, not about verdicts.
"""
import pytest

from document_extraction.adapters.bundle_sample_reads import (
    BROKEN_STRANGER_SELLER_FILENAME,
    BUNDLE_SPECS,
    CLEAN_CHAIN_FILENAME,
    GAP_EXTENT_OVERFLOW_FILENAME,
    PAGES_PER_DEED,
    WEAK_TRANSLITERATION_FILENAME,
)
from document_scrutiny.constants.chain_constants import TitleRole
from document_scrutiny.constants.report_constants import (
    JourneyEntryKind,
    JourneyVerdict,
    ReportVerdictLevel,
)
from document_scrutiny.domain.chain_of_title.chain_of_title import ChainOfTitle
from document_scrutiny.domain.chain_of_title.ownership_report import OwnershipReport
from document_scrutiny.dtos.chain_dtos import ChainDeedDTO

THREAD_ID = "thread_1"


def bundle_named(filename: str):
    return next(spec for spec in BUNDLE_SPECS if spec.filename == filename)


def as_chain_deeds(filename: str):
    bundle = bundle_named(filename)
    return [
        ChainDeedDTO(
            document_id=f"document_{index}",
            filename=bundle.filename,
            deed_record=deed.as_deed_record(),
            page_start=index * PAGES_PER_DEED,
            page_end=index * PAGES_PER_DEED + PAGES_PER_DEED - 1,
            read_confidence=0.95,
        )
        for index, deed in enumerate(bundle.deeds)
    ]


def report_for(filename: str):
    deeds = as_chain_deeds(filename)
    return OwnershipReport.compose(
        thread_id=THREAD_ID, deeds=deeds, chain=ChainOfTitle.validate(deeds=deeds)
    )


def owners(report):
    return [
        entry
        for entry in report.journey
        if entry.kind == JourneyEntryKind.OWNER.value
    ]


def transfers(report):
    return [
        entry
        for entry in report.journey
        if entry.kind == JourneyEntryKind.TRANSFER.value
    ]


class TestTheVerdictTheOfficerReadsFirst:
    def test_an_unbroken_chain_is_described_as_tracing_cleanly(self):
        # Act
        report = report_for(CLEAN_CHAIN_FILENAME)

        # Assert
        assert report.verdict.level == ReportVerdictLevel.CLEAN.value
        assert "2003" in report.verdict.headline
        assert "3 registered deeds" in report.verdict.plain

    def test_a_transliterated_name_is_described_as_one_thing_to_check(self):
        # Act
        report = report_for(WEAK_TRANSLITERATION_FILENAME)

        # Assert
        assert report.verdict.level == ReportVerdictLevel.REVIEW.value
        assert "1 thing need" in report.verdict.headline
        assert "approximate name match" in report.verdict.plain

    def test_an_unsourced_extent_is_described_as_a_possible_missing_deed(self):
        # Act
        report = report_for(GAP_EXTENT_OVERFLOW_FILENAME)

        # Assert
        assert report.verdict.level == ReportVerdictLevel.REVIEW.value
        assert "may be missing a deed" in report.verdict.plain

    def test_a_break_is_said_plainly_and_not_softened(self):
        # Act
        report = report_for(BROKEN_STRANGER_SELLER_FILENAME)

        # Assert
        assert report.verdict.level == ReportVerdictLevel.BROKEN.value
        assert report.verdict.headline == "The title chain is broken"

    def test_a_lone_deed_is_not_called_clean(self):
        """One deed cannot be traced anywhere; calling that clean would present an
        absence of evidence as evidence."""
        # Arrange
        deeds = as_chain_deeds(CLEAN_CHAIN_FILENAME)[-1:]

        # Act
        report = OwnershipReport.compose(
            thread_id=THREAD_ID, deeds=deeds, chain=ChainOfTitle.validate(deeds=deeds)
        )

        # Assert
        assert report.verdict.level == ReportVerdictLevel.REVIEW.value
        assert "Ask for the link documents" in report.verdict.plain

    def test_a_thread_with_nothing_that_conveys_title_says_so(self):
        # Act
        report = OwnershipReport.compose(
            thread_id=THREAD_ID, deeds=[], chain=ChainOfTitle.validate(deeds=[])
        )

        # Assert
        assert report.verdict.headline == "No registered deed to trace"
        assert report.deed_count == 0


class TestTheOwnershipJourney:
    def test_it_runs_from_the_current_owner_back_to_the_root(self):
        # Act
        journey_owners = owners(report_for(CLEAN_CHAIN_FILENAME))

        # Assert
        assert [entry.party.name for entry in journey_owners] == [
            "Prakash Iyer",
            "Sunita Sharma",
            "Ramesh Kumar",
            "Govind Rao",
        ]

    def test_the_current_owner_is_marked_as_holding_it_today(self):
        # Act
        journey_owners = owners(report_for(CLEAN_CHAIN_FILENAME))

        # Assert
        assert journey_owners[0].is_current is True
        assert journey_owners[0].badge == "TITLE OWNER"
        assert not any(entry.is_current for entry in journey_owners[1:])

    def test_the_earliest_deed_is_marked_as_the_mother_deed(self):
        # Act
        journey_owners = owners(report_for(CLEAN_CHAIN_FILENAME))

        # Assert
        assert journey_owners[-1].badge == "MOTHER DEED"
        assert "Root of title" in journey_owners[-1].role
        assert "1188/2003" in journey_owners[-1].meta

    def test_each_transfer_names_the_deed_that_made_it(self):
        # Act
        journey_transfers = transfers(report_for(CLEAN_CHAIN_FILENAME))

        # Assert
        assert [entry.reference.split(" · ")[1] for entry in journey_transfers] == [
            "5820/2019",
            "2451/2011",
            "1188/2003",
        ]

    def test_the_earliest_transfer_is_the_origin_rather_than_a_link(self):
        """There is nothing before it to link to."""
        # Act
        journey_transfers = transfers(report_for(CLEAN_CHAIN_FILENAME))

        # Assert
        assert journey_transfers[-1].verdict == JourneyVerdict.ORIGIN.value
        assert journey_transfers[-1].label == "Origin — root deed"

    def test_a_transfer_carries_its_verdict_as_words_not_as_a_glyph(self):
        """Which icon to draw is the interface's decision."""
        # Act
        journey_transfers = transfers(report_for(BROKEN_STRANGER_SELLER_FILENAME))

        # Assert
        broken = journey_transfers[0]
        assert broken.verdict == "broken"
        assert broken.label == "Break"

    def test_a_weak_transfer_carries_the_score_that_made_it_weak(self):
        # Act
        journey_transfers = transfers(report_for(WEAK_TRANSLITERATION_FILENAME))

        # Assert
        assert 60 <= journey_transfers[0].identity_score < 85
        assert "verify this is the same person" in journey_transfers[0].note

    def test_a_clean_transfer_has_nothing_to_add(self):
        # Act
        journey_transfers = transfers(report_for(CLEAN_CHAIN_FILENAME))

        # Assert
        assert journey_transfers[0].verdict == "linked"
        assert journey_transfers[0].note is None


class TestWhatTheOfficerHasToChase:
    def test_a_clean_chain_leaves_nothing_to_chase(self):
        # Act
        report = report_for(CLEAN_CHAIN_FILENAME)

        # Assert
        assert report.attention == ()

    def test_a_break_is_listed_with_what_to_do_about_it(self):
        # Act
        report = report_for(BROKEN_STRANGER_SELLER_FILENAME)

        # Assert
        assert len(report.attention) == 1
        item = report.attention[0]
        assert item.severity == "high"
        assert item.verb == "RESOLVE"
        assert "legal title opinion" in item.action

    def test_a_weak_link_asks_the_officer_to_verify_rather_than_resolve(self):
        # Act
        report = report_for(WEAK_TRANSLITERATION_FILENAME)

        # Assert
        assert report.attention[0].verb == "VERIFY"
        assert "one-and-the-same affidavit" in report.attention[0].action

    def test_a_gap_asks_for_the_deed_or_an_encumbrance_certificate(self):
        # Act
        report = report_for(GAP_EXTENT_OVERFLOW_FILENAME)

        # Assert
        assert "encumbrance certificate" in report.attention[0].action


class TestWhatTheReportSaysAboutTheDocuments:
    def test_every_deed_is_listed_under_the_role_it_played(self):
        # Act
        report = report_for(CLEAN_CHAIN_FILENAME)

        # Assert
        assert len(report.documents_by_role[TitleRole.TITLE.value]) == 3
        assert report.documents_by_role[TitleRole.AUTHORITY.value] == ()
        assert report.documents_by_role[TitleRole.METADATA.value] == ()

    def test_the_root_deed_is_marked_as_such_in_the_list(self):
        # Act
        report = report_for(CLEAN_CHAIN_FILENAME)
        rows = report.documents_by_role[TitleRole.TITLE.value]

        # Assert
        assert [row.is_root for row in rows] == [True, False, False]

    def test_the_property_is_described_from_the_fullest_deed(self):
        """A photocopied old deed often names only a survey number."""
        # Act
        report = report_for(CLEAN_CHAIN_FILENAME)

        # Assert
        assert report.property_summary.survey_no == "142/2"
        assert report.property_summary.plot_no == "17"
        assert report.property_summary.locality == "Kondapur"

    def test_the_span_of_the_chain_is_reported(self):
        # Act
        report = report_for(CLEAN_CHAIN_FILENAME)

        # Assert
        assert report.stats.title_deed_count == 3
        assert report.stats.span_from == "2003"
        assert report.stats.span_to == "2019"
        assert report.stats.breaks == 0


class TestTheRiskPictureIsDisplayOnly:
    @pytest.mark.parametrize(
        "filename",
        [
            CLEAN_CHAIN_FILENAME,
            WEAK_TRANSLITERATION_FILENAME,
            GAP_EXTENT_OVERFLOW_FILENAME,
            BROKEN_STRANGER_SELLER_FILENAME,
        ],
    )
    def test_the_chain_verdict_is_the_same_whether_or_not_risk_is_read(
        self, filename
    ):
        """Risk summarises; it never decides. The chain verdict is reached without it."""
        # Arrange
        deeds = as_chain_deeds(filename)
        chain = ChainOfTitle.validate(deeds=deeds)

        # Act
        report = OwnershipReport.compose(
            thread_id=THREAD_ID, deeds=deeds, chain=chain
        )

        # Assert
        assert report.chain.overall == chain.overall
        assert tuple(link.verdict for link in report.chain.links) == tuple(
            link.verdict for link in chain.links
        )

    def test_a_broken_chain_scores_high_without_changing_the_verdict(self):
        # Act
        report = report_for(BROKEN_STRANGER_SELLER_FILENAME)

        # Assert
        assert report.risk.level == "High"
        assert report.verdict.level == ReportVerdictLevel.BROKEN.value

    def test_a_clean_chain_still_carries_a_risk_picture(self):
        """Its signals are what a clean chain has none of, which is worth saying."""
        # Act
        report = report_for(CLEAN_CHAIN_FILENAME)

        # Assert
        assert report.risk is not None
        assert report.risk.level == "Low"


class TestDuplicatesInABundle:
    def test_the_same_deed_photocopied_twice_is_counted_once(self):
        """The inventory pass is told to over-segment when unsure. Left alone the
        duplicate becomes a transfer from a person to themselves."""
        # Arrange
        deeds = as_chain_deeds(CLEAN_CHAIN_FILENAME)
        twice = deeds + [
            ChainDeedDTO(
                document_id="document_duplicate",
                filename=CLEAN_CHAIN_FILENAME,
                deed_record=deeds[1].deed_record,
                read_confidence=0.5,
            )
        ]

        # Act
        chain = ChainOfTitle.validate(deeds=twice)
        report = OwnershipReport.compose(
            thread_id=THREAD_ID, deeds=twice, chain=chain
        )

        # Assert
        assert chain.duplicate_document_ids == ("document_duplicate",)
        assert report.stats.title_deed_count == 3
        assert report.verdict.level == ReportVerdictLevel.CLEAN.value

    def test_the_better_read_copy_is_the_one_kept(self):
        # Arrange
        deeds = as_chain_deeds(CLEAN_CHAIN_FILENAME)
        better = ChainDeedDTO(
            document_id="document_better",
            filename=CLEAN_CHAIN_FILENAME,
            deed_record=deeds[1].deed_record,
            read_confidence=0.99,
        )

        # Act
        chain = ChainOfTitle.validate(deeds=deeds + [better])

        # Assert
        assert chain.duplicate_document_ids == ("document_1",)
        assert "document_better" in chain.ordered_document_ids
