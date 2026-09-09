import pytest

from document_extraction.dtos.extraction_dtos import DocumentSegmentDTO
from document_scrutiny.constants.enums import (
    CheckStatus,
    DocumentStage,
    DocumentStatus,
)
from document_scrutiny.dtos.bundle_dtos import SegmentBundleRequestDTO
from document_scrutiny.dtos.thread_dtos import (
    AddDocumentsToThreadDTO,
    CreateScrutinyThreadDTO,
    StoredFileDTO,
)

BUNDLE_FILENAME = "01_clean_chain.pdf"
BUNDLE_APPLICATION_ID = "BN/2026/0455"


def segment(
    page_start: int,
    page_end: int,
    document_type_id: str = "link_doc",
    label: str = "Link document",
) -> DocumentSegmentDTO:
    return DocumentSegmentDTO(
        document_type_id=document_type_id,
        document_type_label=label,
        type_confidence=0.93,
        implemented=True,
        page_start=page_start,
        page_end=page_end,
    )


THREE_DEEDS = (
    segment(0, 1),
    segment(2, 3),
    segment(4, 5, document_type_id="sale_deed", label="Sale deed"),
)


class TestSegmentBundleInteractor:
    @pytest.fixture
    def storage(self):
        from document_scrutiny.storages.in_memory_scrutiny_thread_storage import (
            InMemoryScrutinyThreadStorage,
        )

        return InMemoryScrutinyThreadStorage()

    @pytest.fixture
    def interactor(self, storage):
        from document_scrutiny.interactors.segment_bundle_interactor import (
            SegmentBundleInteractor,
        )

        return SegmentBundleInteractor(thread_storage=storage)

    @pytest.fixture
    def bundle(self, storage):
        thread = storage.create_thread(
            create_thread=CreateScrutinyThreadDTO(
                application_id=BUNDLE_APPLICATION_ID
            )
        )
        document = storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=thread.thread_id,
                stored_files=(
                    StoredFileDTO(
                        filename=BUNDLE_FILENAME,
                        file_format="PDF",
                        file_size_bytes=1038557,
                        stored_path=f"/tmp/uploads/{BUNDLE_FILENAME}",
                    ),
                ),
            )
        )[0]
        return thread, document

    @pytest.fixture
    def segmentation(self, interactor, bundle):
        thread, document = bundle
        return interactor.segment_bundle(
            request=SegmentBundleRequestDTO(
                thread_id=thread.thread_id,
                document_id=document.document_id,
                segments=THREE_DEEDS,
            )
        )

    def test_every_document_found_becomes_a_document_of_its_own(self, segmentation):
        # Assert
        assert len(segmentation.children) == 3
        assert [
            (child.page_start, child.page_end) for child in segmentation.children
        ] == [(0, 1), (2, 3), (4, 5)]

    def test_each_child_points_back_at_the_file_it_came_out_of(
        self, segmentation, bundle
    ):
        # Arrange
        _, document = bundle

        # Assert
        assert all(
            child.parent_document_id == document.document_id
            for child in segmentation.children
        )

    def test_each_child_keeps_the_name_of_the_file_it_came_out_of(self, segmentation):
        """That is where the officer will look for it; the page range says which part."""
        # Assert
        assert all(
            child.filename == BUNDLE_FILENAME for child in segmentation.children
        )

    def test_only_the_deed_being_relied_on_is_listed_as_the_sale_deed(
        self, segmentation
    ):
        # Assert
        assert [child.document_type_id for child in segmentation.children] == [
            "link_doc",
            "link_doc",
            "sale_deed",
        ]

    def test_the_bundle_itself_is_closed_off_rather_than_read(self, segmentation):
        """A file holding four deeds has no single vendor or extent to check against
        the application, so there is nothing to read off it."""
        # Assert
        assert segmentation.parent.stage == DocumentStage.DONE.value
        assert segmentation.parent.field_values == ()

    def test_the_bundle_records_what_was_found_in_it(self, segmentation):
        # Assert
        assert len(segmentation.parent.checks) == 1
        check = segmentation.parent.checks[0]
        assert check.status == CheckStatus.INFO.value
        assert check.title == "3 documents found in this file"

    def test_the_bundle_leaves_the_officer_nothing_to_resolve(self, segmentation):
        # Assert
        assert segmentation.parent.status == DocumentStatus.VERIFIED.value

    def test_the_thread_now_carries_the_bundle_and_its_contents(
        self, segmentation, storage, bundle
    ):
        # Arrange
        thread, _ = bundle

        # Act
        reloaded = storage.get_thread(thread_id=thread.thread_id)

        # Assert
        assert len(reloaded.documents) == 4

    def test_a_child_is_read_from_its_parents_file(self, segmentation, storage, bundle):
        # Arrange
        from document_scrutiny.dtos.thread_dtos import DocumentLookupDTO

        thread, _ = bundle

        # Act
        file_path = storage.get_document_file_path(
            lookup=DocumentLookupDTO(
                thread_id=thread.thread_id,
                document_id=segmentation.children[1].document_id,
            )
        )

        # Assert
        assert file_path == f"/tmp/uploads/{BUNDLE_FILENAME}"

    def test_the_children_are_left_queued_for_the_next_pass_to_read(self, segmentation):
        # Assert
        assert all(
            child.stage == DocumentStage.QUEUED.value
            for child in segmentation.children
        )
