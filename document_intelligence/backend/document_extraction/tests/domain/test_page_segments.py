from document_catalog.constants.enums import DocumentTypeEnum
from document_extraction.domain.page_segments import PageSegments
from document_extraction.dtos.inventory_dtos import PageBoundaryDTO


def boundary(
    page: int, starts: bool = True, doc_type: str = "Sale Deed", summary=None
) -> PageBoundaryDTO:
    return PageBoundaryDTO(
        page=page, starts_new_document=starts, doc_type=doc_type, summary=summary
    )


class TestGroupingPagesIntoDocuments:
    def test_a_document_runs_until_the_page_before_the_next_one_begins(self):
        # Arrange
        boundaries = (boundary(0), boundary(2, doc_type="Gift Deed"), boundary(4))

        # Act
        segments = PageSegments.group(boundaries=boundaries, page_count=6)

        # Assert
        assert [(segment.page_start, segment.page_end) for segment in segments] == [
            (0, 1),
            (2, 3),
            (4, 5),
        ]

    def test_the_last_document_runs_to_the_end_of_the_file(self):
        # Arrange
        boundaries = (boundary(0), boundary(3))

        # Act
        segments = PageSegments.group(boundaries=boundaries, page_count=9)

        # Assert
        assert segments[-1].page_end == 8

    def test_the_first_page_starts_a_document_even_when_the_model_says_otherwise(self):
        """Otherwise a file comes back with no documents in it at all, and every
        page of a genuine deed is silently dropped."""
        # Arrange
        boundaries = (boundary(0, starts=False), boundary(2))

        # Act
        segments = PageSegments.group(boundaries=boundaries, page_count=4)

        # Assert
        assert len(segments) == 2
        assert segments[0].page_start == 0

    def test_a_file_nobody_labelled_still_reports_one_document(self):
        # Act
        segments = PageSegments.group(boundaries=(), page_count=5)

        # Assert
        assert len(segments) == 1
        assert (segments[0].page_start, segments[0].page_end) == (0, 4)

    def test_a_page_outside_the_file_is_ignored(self):
        # Arrange
        boundaries = (boundary(0), boundary(7))

        # Act
        segments = PageSegments.group(boundaries=boundaries, page_count=3)

        # Assert
        assert len(segments) == 1
        assert segments[0].page_end == 2

    def test_an_empty_file_reports_no_documents(self):
        # Act & Assert
        assert PageSegments.group(boundaries=(boundary(0),), page_count=0) == ()

    def test_a_pages_own_summary_is_carried_onto_the_document_it_starts(self):
        # Arrange
        boundaries = (boundary(0, summary="2003 sale: Govind Rao -> Ramesh Kumar"),)

        # Act
        segments = PageSegments.group(boundaries=boundaries, page_count=2)

        # Assert
        assert segments[0].summary == "2003 sale: Govind Rao -> Ramesh Kumar"


class TestTellingTitleDeedsApart:
    def test_a_registered_sale_conveys_title(self):
        assert PageSegments.is_title_doc("Sale Deed") is True

    def test_a_gift_or_partition_conveys_title_too(self):
        assert PageSegments.is_title_doc("Partition Deed") is True
        assert PageSegments.is_title_doc("Gift Deed") is True

    def test_an_agreement_to_sell_conveys_nothing(self):
        """It is a promise to convey later, so it must not be read as a link in the
        chain — which is the whole reason the word disqualifies a match."""
        assert PageSegments.is_title_doc("Agreement of Sale") is False

    def test_a_supporting_paper_conveys_nothing(self):
        assert PageSegments.is_title_doc("Encumbrance Certificate") is False
        assert PageSegments.is_title_doc("") is False


class TestNamingWhatWasFoundInCatalogTerms:
    def test_a_sale_deed_is_recognised(self):
        assert (
            PageSegments.resolve_document_type_id("Sale Deed")
            == DocumentTypeEnum.SALE_DEED.value
        )

    def test_a_title_deed_that_is_not_a_sale_is_a_link_document(self):
        """The catalog has no gift or partition type, and 'link document' is its name
        for a prior deed in the chain — which is exactly what this is."""
        assert (
            PageSegments.resolve_document_type_id("Gift Deed")
            == DocumentTypeEnum.LINK_DOCUMENT.value
        )

    def test_a_supporting_paper_is_named_by_keyword(self):
        assert (
            PageSegments.resolve_document_type_id("Encumbrance Certificate")
            == DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE.value
        )

    def test_something_unrecognised_is_left_unknown_rather_than_guessed(self):
        assert (
            PageSegments.resolve_document_type_id("Registration Summary")
            == DocumentTypeEnum.UNKNOWN.value
        )


class TestOnlyTheLastTitleDeedIsTheOneBeingReliedOn:
    def test_earlier_sale_deeds_in_a_bundle_become_link_documents(self):
        """A bundle is the current deed photocopied with the deeds behind it. Read
        every one of them as the current deed and the officer is asked why a 2003
        vendor is not the applicant."""
        # Arrange
        boundaries = (boundary(0), boundary(2), boundary(4))

        # Act
        segments = PageSegments.group(boundaries=boundaries, page_count=6)

        # Assert
        assert [segment.document_type_id for segment in segments] == [
            DocumentTypeEnum.LINK_DOCUMENT.value,
            DocumentTypeEnum.LINK_DOCUMENT.value,
            DocumentTypeEnum.SALE_DEED.value,
        ]

    def test_a_lone_sale_deed_is_left_as_the_sale_deed(self):
        # Act
        segments = PageSegments.group(boundaries=(boundary(0),), page_count=2)

        # Assert
        assert segments[0].document_type_id == DocumentTypeEnum.SALE_DEED.value

    def test_a_supporting_paper_is_not_reassigned(self):
        # Arrange
        boundaries = (
            boundary(0, doc_type="Encumbrance Certificate"),
            boundary(1),
            boundary(3),
        )

        # Act
        segments = PageSegments.group(boundaries=boundaries, page_count=5)

        # Assert
        assert [segment.document_type_id for segment in segments] == [
            DocumentTypeEnum.ENCUMBRANCE_CERTIFICATE.value,
            DocumentTypeEnum.LINK_DOCUMENT.value,
            DocumentTypeEnum.SALE_DEED.value,
        ]


class TestAFileHoldingOneDocument:
    def test_it_is_reported_as_one_segment_spanning_every_page(self):
        """Stated as a segment so no caller has to tell one document from several."""
        # Act
        segments = PageSegments.single(
            page_count=4, document_type_id=DocumentTypeEnum.PAN.value
        )

        # Assert
        assert len(segments) == 1
        assert (segments[0].page_start, segments[0].page_end) == (0, 3)

    def test_a_card_is_not_a_title_deed(self):
        # Act
        segments = PageSegments.single(
            page_count=1, document_type_id=DocumentTypeEnum.PAN.value
        )

        # Assert
        assert segments[0].is_title_doc is False

    def test_a_deed_is(self):
        # Act
        segments = PageSegments.single(
            page_count=1, document_type_id=DocumentTypeEnum.LINK_DOCUMENT.value
        )

        # Assert
        assert segments[0].is_title_doc is True
