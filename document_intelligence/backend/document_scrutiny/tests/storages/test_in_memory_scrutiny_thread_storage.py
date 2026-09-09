import pytest

from document_scrutiny.constants.enums import DocumentStage, DocumentStatus
from document_scrutiny.dtos.thread_dtos import (
    AddChildDocumentsDTO,
    AddDocumentsToThreadDTO,
    ChildDocumentDTO,
    CreateScrutinyThreadDTO,
    DocumentLookupDTO,
    StoredFileDTO,
    UpdateDocumentDTO,
    UpdateServiceOverridesDTO,
)
from document_scrutiny.exceptions.scrutiny_exceptions import (
    DocumentNotFound,
    ScrutinyThreadNotFound,
)

CLEAN_APPLICATION_ID = "BN/2026/0421"


def build_stored_file(filename: str = "pan_card.pdf") -> StoredFileDTO:
    return StoredFileDTO(
        filename=filename,
        file_format="PDF",
        file_size_bytes=188000,
        stored_path=f"/tmp/uploads/{filename}",
    )


class TestInMemoryScrutinyThreadStorage:
    @pytest.fixture
    def storage(self):
        from document_scrutiny.storages.in_memory_scrutiny_thread_storage import (
            InMemoryScrutinyThreadStorage,
        )

        return InMemoryScrutinyThreadStorage()

    @pytest.fixture
    def thread(self, storage):
        return storage.create_thread(
            create_thread=CreateScrutinyThreadDTO(application_id=CLEAN_APPLICATION_ID)
        )

    def test_reading_a_thread_nobody_created_raises(self, storage):
        # Arrange
        unknown_thread_id = "thread_missing"

        # Act & Assert
        with pytest.raises(ScrutinyThreadNotFound) as exception_info:
            storage.get_thread(thread_id=unknown_thread_id)
        assert exception_info.value.thread_id == unknown_thread_id

    def test_adding_documents_to_a_thread_nobody_created_raises(self, storage):
        # Arrange
        add_documents = AddDocumentsToThreadDTO(
            thread_id="thread_missing", stored_files=(build_stored_file(),)
        )

        # Act & Assert
        with pytest.raises(ScrutinyThreadNotFound):
            storage.add_documents(add_documents=add_documents)

    def test_reading_a_document_nobody_added_raises(self, storage, thread):
        # Arrange
        lookup = DocumentLookupDTO(
            thread_id=thread.thread_id, document_id="document_missing"
        )

        # Act & Assert
        with pytest.raises(DocumentNotFound) as exception_info:
            storage.get_document(lookup=lookup)
        assert exception_info.value.document_id == "document_missing"
        assert exception_info.value.thread_id == thread.thread_id

    def test_a_new_thread_starts_empty_with_no_forced_service_outcomes(self, thread):
        # Arrange
        # Act
        # Assert
        assert thread.application_id == CLEAN_APPLICATION_ID
        assert thread.documents == ()
        assert thread.service_overrides == {}
        assert thread.thread_id

    def test_each_thread_gets_its_own_identifier(self, storage):
        # Arrange
        create_thread = CreateScrutinyThreadDTO(application_id=CLEAN_APPLICATION_ID)

        # Act
        first = storage.create_thread(create_thread=create_thread)
        second = storage.create_thread(create_thread=create_thread)

        # Assert
        assert first.thread_id != second.thread_id

    def test_added_documents_are_queued_and_carry_their_file_details(self, storage, thread):
        # Arrange
        add_documents = AddDocumentsToThreadDTO(
            thread_id=thread.thread_id,
            stored_files=(build_stored_file(), build_stored_file("second.jpg")),
        )

        # Act
        documents = storage.add_documents(add_documents=add_documents)

        # Assert
        assert len(documents) == 2
        assert [document.filename for document in documents] == [
            "pan_card.pdf",
            "second.jpg",
        ]
        assert documents[0].stage == DocumentStage.QUEUED.value
        assert documents[0].status == DocumentStatus.CHECKING.value
        assert documents[0].file_size_bytes == 188000
        assert documents[0].document_type_id is None

    def test_each_document_gets_its_own_identifier(self, storage, thread):
        # Arrange
        add_documents = AddDocumentsToThreadDTO(
            thread_id=thread.thread_id,
            stored_files=(build_stored_file(), build_stored_file()),
        )

        # Act
        documents = storage.add_documents(add_documents=add_documents)

        # Assert
        assert documents[0].document_id != documents[1].document_id

    def test_the_thread_reports_the_documents_added_to_it(self, storage, thread):
        # Arrange
        storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=thread.thread_id, stored_files=(build_stored_file(),)
            )
        )

        # Act
        reloaded = storage.get_thread(thread_id=thread.thread_id)

        # Assert
        assert len(reloaded.documents) == 1

    def test_the_stored_file_path_is_kept_off_the_document_the_officer_sees(
        self, storage, thread
    ):
        # Arrange — a server path must never travel to the browser
        documents = storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=thread.thread_id, stored_files=(build_stored_file(),)
            )
        )

        # Act
        file_path = storage.get_document_file_path(
            lookup=DocumentLookupDTO(
                thread_id=thread.thread_id, document_id=documents[0].document_id
            )
        )

        # Assert
        assert file_path == "/tmp/uploads/pan_card.pdf"
        assert not hasattr(documents[0], "stored_path")

    def test_an_updated_document_replaces_the_one_held(self, storage, thread):
        # Arrange
        documents = storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=thread.thread_id, stored_files=(build_stored_file(),)
            )
        )
        advanced = type(documents[0])(
            **{
                **documents[0].__dict__,
                "stage": DocumentStage.DONE.value,
                "status": DocumentStatus.VERIFIED.value,
            }
        )

        # Act
        updated = storage.update_document(
            update_document=UpdateDocumentDTO(
                thread_id=thread.thread_id, document=advanced
            )
        )

        # Assert
        assert updated.stage == DocumentStage.DONE.value
        reloaded = storage.get_thread(thread_id=thread.thread_id)
        assert reloaded.documents[0].status == DocumentStatus.VERIFIED.value

    def test_updating_a_document_nobody_added_raises(self, storage, thread):
        # Arrange
        documents = storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=thread.thread_id, stored_files=(build_stored_file(),)
            )
        )
        stranger = type(documents[0])(
            **{**documents[0].__dict__, "document_id": "document_stranger"}
        )

        # Act & Assert
        with pytest.raises(DocumentNotFound):
            storage.update_document(
                update_document=UpdateDocumentDTO(
                    thread_id=thread.thread_id, document=stranger
                )
            )

    def test_forced_service_outcomes_are_recorded_against_the_thread(self, storage, thread):
        # Arrange
        overrides = {"itd_pan": "timeout"}

        # Act
        updated = storage.update_service_overrides(
            update_overrides=UpdateServiceOverridesDTO(
                thread_id=thread.thread_id, service_overrides=overrides
            )
        )

        # Assert
        assert updated.service_overrides == overrides
        assert storage.get_thread(thread_id=thread.thread_id).service_overrides == overrides

    def test_two_threads_do_not_share_documents(self, storage):
        # Arrange
        first = storage.create_thread(
            create_thread=CreateScrutinyThreadDTO(application_id=CLEAN_APPLICATION_ID)
        )
        second = storage.create_thread(
            create_thread=CreateScrutinyThreadDTO(application_id=CLEAN_APPLICATION_ID)
        )

        # Act
        storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=first.thread_id, stored_files=(build_stored_file(),)
            )
        )

        # Assert
        assert len(storage.get_thread(thread_id=first.thread_id).documents) == 1
        assert storage.get_thread(thread_id=second.thread_id).documents == ()

class TestDocumentsFoundInsideABundle:
    @pytest.fixture
    def storage(self):
        from document_scrutiny.storages.in_memory_scrutiny_thread_storage import (
            InMemoryScrutinyThreadStorage,
        )

        return InMemoryScrutinyThreadStorage()

    @pytest.fixture
    def thread(self, storage):
        return storage.create_thread(
            create_thread=CreateScrutinyThreadDTO(application_id=CLEAN_APPLICATION_ID)
        )

    @pytest.fixture
    def bundle(self, storage, thread):
        return storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=thread.thread_id,
                stored_files=(build_stored_file("01_clean_chain.pdf"),),
            )
        )[0]

    @staticmethod
    def build_child(
        page_start: int, page_end: int, document_type_id: str = "link_doc"
    ) -> ChildDocumentDTO:
        return ChildDocumentDTO(
            filename="01_clean_chain.pdf",
            file_format="PDF",
            file_size_bytes=1038557,
            document_type_id=document_type_id,
            document_type_label="Link document",
            type_confidence=0.93,
            implemented=True,
            page_start=page_start,
            page_end=page_end,
        )

    def test_each_document_found_is_listed_in_its_own_right(
        self, storage, thread, bundle
    ):
        # Arrange
        children = (self.build_child(0, 1), self.build_child(2, 3))

        # Act
        added = storage.add_child_documents(
            add_children=AddChildDocumentsDTO(
                thread_id=thread.thread_id,
                parent_document_id=bundle.document_id,
                children=children,
            )
        )

        # Assert
        assert len(added) == 2
        assert added[0].document_id != added[1].document_id
        assert [
            (document.page_start, document.page_end) for document in added
        ] == [(0, 1), (2, 3)]

    def test_a_child_arrives_already_identified(self, storage, thread, bundle):
        """The pass that found it inside the file is the one that could tell what it
        was; a slice read on its own cannot know it sits behind a later deed."""
        # Act
        added = storage.add_child_documents(
            add_children=AddChildDocumentsDTO(
                thread_id=thread.thread_id,
                parent_document_id=bundle.document_id,
                children=(self.build_child(0, 1),),
            )
        )

        # Assert
        assert added[0].document_type_id == "link_doc"
        assert added[0].document_type_label == "Link document"
        assert added[0].implemented is True
        assert added[0].stage == DocumentStage.QUEUED.value

    def test_a_child_knows_how_many_pages_it_covers(self, storage, thread, bundle):
        # Act
        added = storage.add_child_documents(
            add_children=AddChildDocumentsDTO(
                thread_id=thread.thread_id,
                parent_document_id=bundle.document_id,
                children=(self.build_child(2, 5),),
            )
        )

        # Assert
        assert added[0].page_count == 4

    def test_children_are_listed_next_to_the_file_they_came_out_of(
        self, storage, thread, bundle
    ):
        # Arrange — a second file is attached after the bundle
        storage.add_documents(
            add_documents=AddDocumentsToThreadDTO(
                thread_id=thread.thread_id, stored_files=(build_stored_file("pan.jpg"),)
            )
        )

        # Act
        storage.add_child_documents(
            add_children=AddChildDocumentsDTO(
                thread_id=thread.thread_id,
                parent_document_id=bundle.document_id,
                children=(self.build_child(0, 1), self.build_child(2, 3)),
            )
        )

        # Assert — the officer reads a bundle and its contents together
        reloaded = storage.get_thread(thread_id=thread.thread_id)
        assert [document.filename for document in reloaded.documents] == [
            "01_clean_chain.pdf",
            "01_clean_chain.pdf",
            "01_clean_chain.pdf",
            "pan.jpg",
        ]

    def test_a_child_is_read_from_the_file_its_parent_stored(
        self, storage, thread, bundle
    ):
        """It has no file of its own: it is a page range of the parent's."""
        # Arrange
        added = storage.add_child_documents(
            add_children=AddChildDocumentsDTO(
                thread_id=thread.thread_id,
                parent_document_id=bundle.document_id,
                children=(self.build_child(2, 3),),
            )
        )

        # Act
        file_path = storage.get_document_file_path(
            lookup=DocumentLookupDTO(
                thread_id=thread.thread_id, document_id=added[0].document_id
            )
        )

        # Assert
        assert file_path == "/tmp/uploads/01_clean_chain.pdf"

    def test_a_document_nobody_added_has_no_file(self, storage, thread):
        # Act
        file_path = storage.get_document_file_path(
            lookup=DocumentLookupDTO(
                thread_id=thread.thread_id, document_id="document_missing"
            )
        )

        # Assert
        assert file_path is None

    def test_segmenting_a_file_nobody_added_raises(self, storage, thread):
        # Act & Assert
        with pytest.raises(DocumentNotFound):
            storage.add_child_documents(
                add_children=AddChildDocumentsDTO(
                    thread_id=thread.thread_id,
                    parent_document_id="document_missing",
                    children=(self.build_child(0, 1),),
                )
            )
