import pytest

from document_extraction.adapters.bundle_sample_reads import (
    BROKEN_STRANGER_SELLER_FILENAME,
    CLEAN_CHAIN_FILENAME,
    PAGES_PER_DEED,
    BUNDLE_SPECS,
)
from document_scrutiny.constants.chain_constants import ChainVerdict
from document_scrutiny.constants.enums import DocumentStage, DocumentStatus
from document_scrutiny.dtos.chain_dtos import ChainOfTitleRequestDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO
from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO

THREAD_ID = "thread_1"
BUNDLE_APPLICATION_ID = "BN/2026/0455"


def bundle_named(filename: str):
    return next(spec for spec in BUNDLE_SPECS if spec.filename == filename)


def deed_document(document_id: str, deed, page_start: int) -> DocumentStateDTO:
    return DocumentStateDTO(
        document_id=document_id,
        filename=deed.filename,
        file_format="PDF",
        file_size_bytes=1000,
        document_type_id=deed.document_type_id,
        document_type_label="Sale deed",
        type_confidence=0.95,
        implemented=True,
        stage=DocumentStage.DONE.value,
        status=DocumentStatus.VERIFIED.value,
        confirmed=False,
        page_count=PAGES_PER_DEED,
        deed_record=deed.as_deed_record(),
        parent_document_id="document_bundle",
        page_start=page_start,
        page_end=page_start + PAGES_PER_DEED - 1,
    )


def card_document() -> DocumentStateDTO:
    return DocumentStateDTO(
        document_id="document_card",
        filename="pan_card.pdf",
        file_format="PDF",
        file_size_bytes=188000,
        document_type_id="pan",
        document_type_label="PAN",
        type_confidence=0.99,
        implemented=True,
        stage=DocumentStage.DONE.value,
        status=DocumentStatus.VERIFIED.value,
        confirmed=False,
        page_count=1,
    )


def bundle_parent_document() -> DocumentStateDTO:
    return DocumentStateDTO(
        document_id="document_bundle",
        filename=CLEAN_CHAIN_FILENAME,
        file_format="PDF",
        file_size_bytes=1038557,
        document_type_id="sale_deed",
        document_type_label="Sale deed",
        type_confidence=0.94,
        implemented=True,
        stage=DocumentStage.DONE.value,
        status=DocumentStatus.VERIFIED.value,
        confirmed=False,
        page_count=6,
    )


class TestGetChainOfTitleInteractor:
    @pytest.fixture
    def thread_storage(self):
        from unittest.mock import create_autospec

        from document_scrutiny.storage_interfaces.scrutiny_thread_storage_interface import (
            ScrutinyThreadStorageInterface,
        )

        return create_autospec(ScrutinyThreadStorageInterface)

    @pytest.fixture
    def interactor(self, thread_storage):
        from document_scrutiny.interactors.get_chain_of_title_interactor import (
            GetChainOfTitleInteractor,
        )

        return GetChainOfTitleInteractor(thread_storage=thread_storage)

    def hold(self, thread_storage, documents) -> None:
        thread_storage.get_thread.return_value = ScrutinyThreadDTO(
            thread_id=THREAD_ID,
            application_id=BUNDLE_APPLICATION_ID,
            documents=tuple(documents),
        )

    def segmented_bundle(self, filename: str):
        bundle = bundle_named(filename)
        return [bundle_parent_document()] + [
            deed_document(
                document_id=f"document_{index}",
                deed=deed,
                page_start=index * PAGES_PER_DEED,
            )
            for index, deed in enumerate(bundle.deeds)
        ]

    def test_a_segmented_bundle_is_traced_end_to_end(self, interactor, thread_storage):
        # Arrange
        self.hold(thread_storage, self.segmented_bundle(CLEAN_CHAIN_FILENAME))

        # Act
        chain = interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=THREAD_ID)
        )

        # Assert
        assert chain.overall == ChainVerdict.INTACT.value
        assert len(chain.links) == 2

    def test_the_bundle_itself_is_not_a_deed_in_its_own_chain(
        self, interactor, thread_storage
    ):
        """It was segmented rather than read, so it carries no record and no transfer."""
        # Arrange
        self.hold(thread_storage, self.segmented_bundle(CLEAN_CHAIN_FILENAME))

        # Act
        chain = interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=THREAD_ID)
        )

        # Assert
        assert "document_bundle" not in chain.ordered_document_ids
        assert len(chain.ordered_document_ids) == 3

    def test_an_identity_card_is_not_part_of_a_chain_of_title(
        self, interactor, thread_storage
    ):
        # Arrange
        self.hold(
            thread_storage,
            self.segmented_bundle(CLEAN_CHAIN_FILENAME) + [card_document()],
        )

        # Act
        chain = interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=THREAD_ID)
        )

        # Assert
        assert "document_card" not in chain.ordered_document_ids
        assert chain.overall == ChainVerdict.INTACT.value

    def test_a_break_in_the_chain_reaches_the_thread_verdict(
        self, interactor, thread_storage
    ):
        # Arrange
        self.hold(thread_storage, self.segmented_bundle(BROKEN_STRANGER_SELLER_FILENAME))

        # Act
        chain = interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=THREAD_ID)
        )

        # Assert
        assert chain.overall == ChainVerdict.BROKEN.value
        assert chain.findings[0].severity == "high"

    def test_a_thread_holding_no_deeds_reports_an_empty_chain(
        self, interactor, thread_storage
    ):
        """A PAN-only thread has no title to trace, and that is not a failure."""
        # Arrange
        self.hold(thread_storage, [card_document()])

        # Act
        chain = interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=THREAD_ID)
        )

        # Assert
        assert chain.ordered_document_ids == ()
        assert chain.links == ()
        assert chain.overall == ChainVerdict.INTACT.value

    def test_deeds_attached_as_separate_files_trace_the_same_way(
        self, interactor, thread_storage
    ):
        """By this point a bundle and a stack of files are indistinguishable, which is
        the point of segmenting into documents rather than special-casing bundles."""
        # Arrange
        bundle = bundle_named(CLEAN_CHAIN_FILENAME)
        loose = [
            DocumentStateDTO(
                document_id=f"document_{index}",
                filename=f"deed_{index}.pdf",
                file_format="PDF",
                file_size_bytes=1000,
                document_type_id=deed.document_type_id,
                document_type_label="Sale deed",
                type_confidence=0.95,
                implemented=True,
                stage=DocumentStage.DONE.value,
                status=DocumentStatus.VERIFIED.value,
                confirmed=False,
                page_count=PAGES_PER_DEED,
                deed_record=deed.as_deed_record(),
            )
            for index, deed in enumerate(bundle.deeds)
        ]
        self.hold(thread_storage, loose)

        # Act
        chain = interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=THREAD_ID)
        )

        # Assert
        assert chain.overall == ChainVerdict.INTACT.value
        assert len(chain.links) == 2
