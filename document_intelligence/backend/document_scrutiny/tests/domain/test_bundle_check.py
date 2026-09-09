from document_extraction.dtos.extraction_dtos import DocumentSegmentDTO
from document_scrutiny.constants.enums import CheckGroup, CheckStatus
from document_scrutiny.domain.bundle_check import BundleCheck
from document_scrutiny.domain.open_check import is_open

DOCUMENT_ID = "document_1"


def segment(
    page_start: int, page_end: int, label: str = "Sale deed"
) -> DocumentSegmentDTO:
    return DocumentSegmentDTO(
        document_type_id="sale_deed",
        document_type_label=label,
        type_confidence=0.94,
        implemented=True,
        page_start=page_start,
        page_end=page_end,
    )


class TestWhatWasFoundInABundle:
    def test_the_officer_is_told_how_many_documents_came_out_of_one_file(self):
        # Arrange
        segments = (
            segment(0, 1, "Link document"),
            segment(2, 3, "Link document"),
            segment(4, 5),
        )

        # Act
        check = BundleCheck.build(document_id=DOCUMENT_ID, segments=segments)

        # Assert
        assert check.title == "3 documents found in this file"

    def test_each_document_is_named_with_the_pages_it_occupies(self):
        # Arrange
        segments = (segment(0, 1, "Link document"), segment(2, 3))

        # Act
        check = BundleCheck.build(document_id=DOCUMENT_ID, segments=segments)

        # Assert
        assert "Pages 1-2: Link document." in check.detail
        assert "Pages 3-4: Sale deed." in check.detail

    def test_pages_are_counted_the_way_the_officer_counts_them(self):
        """Page indexes start at zero inside the file; an officer's do not."""
        # Act
        described = BundleCheck.describe_pages(segment(0, 1))

        # Assert
        assert described == "Pages 1-2"

    def test_a_one_page_document_is_not_described_as_a_range(self):
        # Act & Assert
        assert BundleCheck.describe_pages(segment(4, 4)) == "Page 5"

    def test_nothing_is_wrong_with_a_file_that_holds_several_documents(self):
        """Information, not a finding: the bundle is normal, and each document found
        is scrutinised in its own right."""
        # Act
        check = BundleCheck.build(
            document_id=DOCUMENT_ID, segments=(segment(0, 1), segment(2, 3))
        )

        # Assert
        assert check.status == CheckStatus.INFO.value
        assert check.group == CheckGroup.RULE.value

    def test_it_leaves_the_officer_nothing_to_resolve(self):
        # Act
        check = BundleCheck.build(document_id=DOCUMENT_ID, segments=(segment(0, 1),))

        # Assert
        assert is_open(check) is False

    def test_the_check_is_recorded_against_the_file_it_describes(self):
        # Act
        check = BundleCheck.build(document_id=DOCUMENT_ID, segments=(segment(0, 1),))

        # Assert
        assert check.check_id == f"{DOCUMENT_ID}:bundle"
        assert check.document_id == DOCUMENT_ID
