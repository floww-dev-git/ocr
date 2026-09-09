import pytest

from document_scrutiny.constants.upload_constants import UploadRejectionReason
from document_scrutiny.domain.upload_guard import UploadGuard
from document_scrutiny.dtos.thread_dtos import IncomingFileDTO, UploadLimitsDTO
from document_scrutiny.exceptions.scrutiny_exceptions import UploadRejected

LIMITS = UploadLimitsDTO(
    allowed_extensions=(".pdf", ".jpg", ".jpeg", ".png"), max_bytes=1024
)


class TestUploadGuard:
    @pytest.mark.parametrize(
        "filename", ["notes.txt", "archive.zip", "script.sh", "pan_card", "pan.pdf.exe"]
    )
    def test_a_format_the_reader_cannot_open_is_refused(self, filename):
        # Arrange
        incoming = IncomingFileDTO(filename=filename, content=b"x" * 10)

        # Act & Assert
        with pytest.raises(UploadRejected) as exception_info:
            UploadGuard.check(incoming=incoming, limits=LIMITS)
        assert exception_info.value.reason == UploadRejectionReason.UNSUPPORTED_FORMAT.value
        assert exception_info.value.filename == filename

    def test_a_file_larger_than_the_cap_is_refused_and_the_cap_is_stated(self):
        # Arrange
        incoming = IncomingFileDTO(filename="pan_card.pdf", content=b"x" * 2048)

        # Act & Assert
        with pytest.raises(UploadRejected) as exception_info:
            UploadGuard.check(incoming=incoming, limits=LIMITS)
        assert exception_info.value.reason == UploadRejectionReason.TOO_LARGE.value
        assert "1024 bytes" in exception_info.value.message

    def test_an_empty_file_is_refused(self):
        # Arrange
        incoming = IncomingFileDTO(filename="pan_card.pdf", content=b"")

        # Act & Assert
        with pytest.raises(UploadRejected) as exception_info:
            UploadGuard.check(incoming=incoming, limits=LIMITS)
        assert exception_info.value.reason == UploadRejectionReason.EMPTY_FILE.value

    @pytest.mark.parametrize(
        "filename", ["pan_card.pdf", "PAN_CARD.PDF", "scan.jpeg", "photo.PNG"]
    )
    def test_a_readable_format_is_accepted_whatever_its_case(self, filename):
        # Arrange
        incoming = IncomingFileDTO(filename=filename, content=b"x" * 10)

        # Act
        UploadGuard.check(incoming=incoming, limits=LIMITS)

        # Assert
        assert UploadGuard.read_file_format(filename=filename) in ("PDF", "JPEG", "PNG")

    def test_a_file_exactly_at_the_cap_is_accepted(self):
        # Arrange
        incoming = IncomingFileDTO(filename="pan_card.pdf", content=b"x" * 1024)

        # Act
        UploadGuard.check(incoming=incoming, limits=LIMITS)

        # Assert
        assert len(incoming.content) == 1024

    @pytest.mark.parametrize(
        "filename, expected_format",
        [
            ("pan_card.pdf", "PDF"),
            ("scan.jpg", "JPEG"),
            ("scan.jpeg", "JPEG"),
            ("photo.png", "PNG"),
        ],
    )
    def test_the_format_shown_to_the_officer_is_read_from_the_extension(
        self, filename, expected_format
    ):
        # Arrange
        # Act
        file_format = UploadGuard.read_file_format(filename=filename)

        # Assert
        assert file_format == expected_format

    @pytest.mark.parametrize(
        "hostile_filename",
        [
            "../../etc/passwd.pdf",
            "/etc/shadow.pdf",
            "..\\..\\windows\\system.pdf",
            "pan/../../secret.pdf",
        ],
    )
    def test_a_filename_carrying_a_path_yields_a_stored_name_with_no_path_in_it(
        self, hostile_filename
    ):
        # Arrange — the officer's filename is never a path on this server
        # Act
        stored_name = UploadGuard.build_stored_name(filename=hostile_filename)

        # Assert
        assert "/" not in stored_name
        assert "\\" not in stored_name
        assert ".." not in stored_name
        assert stored_name.endswith(".pdf")

    def test_two_uploads_of_the_same_filename_get_different_stored_names(self):
        # Arrange
        filename = "pan_card.pdf"

        # Act
        first = UploadGuard.build_stored_name(filename=filename)
        second = UploadGuard.build_stored_name(filename=filename)

        # Assert
        assert first != second

    def test_the_stored_name_keeps_the_extension_the_reader_needs(self):
        # Arrange
        # Act
        stored_name = UploadGuard.build_stored_name(filename="Applicant PAN Scan.JPEG")

        # Assert
        assert stored_name.endswith(".jpeg")
        assert "Applicant" not in stored_name
