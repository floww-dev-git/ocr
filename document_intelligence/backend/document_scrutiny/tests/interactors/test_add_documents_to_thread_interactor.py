import pytest

from document_scrutiny.constants.upload_constants import UploadRejectionReason
from document_scrutiny.dtos.thread_dtos import (
    AddDocumentsRequestDTO,
    IncomingFileDTO,
    ScrutinyThreadDTO,
    UploadLimitsDTO,
)
from document_scrutiny.exceptions.scrutiny_exceptions import (
    ScrutinyThreadNotFound,
    UploadRejected,
)
from document_scrutiny.tests.conftest import CLEAN_APPLICATION_ID, ScrutinyStorageMock

THREAD_ID = "thread_1"
READABLE_CONTENT = b"%PDF-1.4 pretend scan"


def build_request(*incoming_files: IncomingFileDTO) -> AddDocumentsRequestDTO:
    return AddDocumentsRequestDTO(thread_id=THREAD_ID, incoming_files=incoming_files)


class TestAddDocumentsToThreadInteractor(ScrutinyStorageMock):
    @pytest.fixture
    def upload_limits(self):
        return UploadLimitsDTO(
            allowed_extensions=(".pdf", ".jpg", ".jpeg", ".png"), max_bytes=1024
        )

    @pytest.fixture
    def interactor(self, thread_storage, document_file_store, upload_limits):
        from document_scrutiny.interactors.add_documents_to_thread_interactor import (
            AddDocumentsToThreadInteractor,
        )

        return AddDocumentsToThreadInteractor(
            thread_storage=thread_storage,
            document_file_store=document_file_store,
            upload_limits=upload_limits,
        )

    @pytest.fixture(autouse=True)
    def existing_thread(self, thread_storage):
        thread_storage.get_thread.return_value = ScrutinyThreadDTO(
            thread_id=THREAD_ID, application_id=CLEAN_APPLICATION_ID
        )

    def test_attaching_to_a_thread_nobody_opened_writes_nothing(
        self, interactor, thread_storage, document_file_store
    ):
        # Arrange
        thread_storage.get_thread.side_effect = ScrutinyThreadNotFound(
            thread_id=THREAD_ID
        )
        request = build_request(
            IncomingFileDTO(filename="pan_card.pdf", content=READABLE_CONTENT)
        )

        # Act & Assert
        with pytest.raises(ScrutinyThreadNotFound):
            interactor.add_documents(request=request)
        document_file_store.write_file.assert_not_called()
        thread_storage.add_documents.assert_not_called()

    def test_a_format_the_reader_cannot_open_writes_nothing(
        self, interactor, document_file_store, thread_storage
    ):
        # Arrange
        request = build_request(
            IncomingFileDTO(filename="notes.txt", content=READABLE_CONTENT)
        )

        # Act & Assert
        with pytest.raises(UploadRejected) as exception_info:
            interactor.add_documents(request=request)
        assert exception_info.value.reason == UploadRejectionReason.UNSUPPORTED_FORMAT.value
        document_file_store.write_file.assert_not_called()
        thread_storage.add_documents.assert_not_called()

    def test_one_unreadable_file_in_a_batch_writes_none_of_them(
        self, interactor, document_file_store, thread_storage
    ):
        # Arrange — every file is checked before any of them is written, so a
        # rejected attachment cannot leave half a batch on disk
        request = build_request(
            IncomingFileDTO(filename="pan_card.pdf", content=READABLE_CONTENT),
            IncomingFileDTO(filename="archive.zip", content=READABLE_CONTENT),
        )

        # Act & Assert
        with pytest.raises(UploadRejected):
            interactor.add_documents(request=request)
        document_file_store.write_file.assert_not_called()
        thread_storage.add_documents.assert_not_called()

    def test_a_file_over_the_cap_writes_nothing_and_states_the_cap(
        self, interactor, document_file_store
    ):
        # Arrange
        request = build_request(
            IncomingFileDTO(filename="pan_card.pdf", content=b"x" * 2048)
        )

        # Act & Assert
        with pytest.raises(UploadRejected) as exception_info:
            interactor.add_documents(request=request)
        assert "1024 bytes" in exception_info.value.message
        document_file_store.write_file.assert_not_called()

    def test_an_empty_attachment_writes_nothing(self, interactor, document_file_store):
        # Arrange
        request = build_request(IncomingFileDTO(filename="pan_card.pdf", content=b""))

        # Act & Assert
        with pytest.raises(UploadRejected) as exception_info:
            interactor.add_documents(request=request)
        assert exception_info.value.reason == UploadRejectionReason.EMPTY_FILE.value
        document_file_store.write_file.assert_not_called()

    def test_a_filename_carrying_a_path_is_stored_under_a_generated_name(
        self, interactor, document_file_store, thread_storage
    ):
        # Arrange
        document_file_store.write_file.return_value = "/uploads/thread_1/generated.pdf"
        thread_storage.add_documents.return_value = []
        request = build_request(
            IncomingFileDTO(filename="../../etc/passwd.pdf", content=READABLE_CONTENT)
        )

        # Act
        interactor.add_documents(request=request)

        # Assert
        write_request = document_file_store.write_file.call_args.kwargs["write_file"]
        assert "/" not in write_request.stored_name
        assert ".." not in write_request.stored_name
        assert write_request.stored_name.endswith(".pdf")
        assert write_request.thread_id == THREAD_ID

    def test_the_officers_filename_is_kept_for_display_but_not_for_disk(
        self, interactor, document_file_store, thread_storage
    ):
        # Arrange
        document_file_store.write_file.return_value = "/uploads/thread_1/generated.pdf"
        thread_storage.add_documents.return_value = []
        request = build_request(
            IncomingFileDTO(filename="Applicant PAN.pdf", content=READABLE_CONTENT)
        )

        # Act
        interactor.add_documents(request=request)

        # Assert
        stored_files = thread_storage.add_documents.call_args.kwargs[
            "add_documents"
        ].stored_files
        assert stored_files[0].filename == "Applicant PAN.pdf"
        assert stored_files[0].stored_path == "/uploads/thread_1/generated.pdf"
        assert "Applicant" not in document_file_store.write_file.call_args.kwargs[
            "write_file"
        ].stored_name

    def test_every_readable_attachment_is_written_then_recorded(
        self, interactor, document_file_store, thread_storage
    ):
        # Arrange
        document_file_store.write_file.side_effect = [
            "/uploads/thread_1/one.pdf",
            "/uploads/thread_1/two.jpg",
        ]
        thread_storage.add_documents.return_value = []
        request = build_request(
            IncomingFileDTO(filename="pan_card.pdf", content=READABLE_CONTENT),
            IncomingFileDTO(filename="pan_back.jpg", content=b"\xff\xd8pretend jpeg"),
        )

        # Act
        interactor.add_documents(request=request)

        # Assert
        assert document_file_store.write_file.call_count == 2
        stored_files = thread_storage.add_documents.call_args.kwargs[
            "add_documents"
        ].stored_files
        assert [stored.file_format for stored in stored_files] == ["PDF", "JPEG"]
        assert [stored.file_size_bytes for stored in stored_files] == [
            len(READABLE_CONTENT),
            len(b"\xff\xd8pretend jpeg"),
        ]

    def test_the_documents_the_storage_recorded_are_returned(
        self, interactor, document_file_store, thread_storage
    ):
        # Arrange
        from document_scrutiny.tests.factories.scrutiny_dto_factories import (
            DocumentStateDTOFactory,
        )

        recorded = DocumentStateDTOFactory.create_batch(size=1)
        document_file_store.write_file.return_value = "/uploads/thread_1/one.pdf"
        thread_storage.add_documents.return_value = recorded
        request = build_request(
            IncomingFileDTO(filename="pan_card.pdf", content=READABLE_CONTENT)
        )

        # Act
        documents = interactor.add_documents(request=request)

        # Assert
        assert documents == recorded

    def test_attaching_nothing_records_nothing(
        self, interactor, document_file_store, thread_storage
    ):
        # Arrange
        request = build_request()
        thread_storage.add_documents.return_value = []

        # Act
        documents = interactor.add_documents(request=request)

        # Assert
        assert documents == []
        document_file_store.write_file.assert_not_called()
        thread_storage.add_documents.assert_not_called()
