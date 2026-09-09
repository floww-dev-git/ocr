"""An officer's correction of a deed field must re-trace the chain.

The chain reasons over the structured deed record, not the flat values the officer
edits. Task 9 carries the edit into the record; these tests prove that a corrected
deed re-traces correctly, over real storage and the real edit + chain interactors.
"""
import pytest

from document_extraction.adapters.bundle_sample_reads import (
    BROKEN_STRANGER_SELLER_FILENAME,
    BUNDLE_SPECS,
    GAP_EXTENT_OVERFLOW_FILENAME,
    PAGES_PER_DEED,
)
from document_scrutiny.constants.chain_constants import ChainVerdict, LinkVerdict
from document_scrutiny.constants.enums import DocumentStage, DocumentStatus
from document_scrutiny.dtos.chain_dtos import ChainOfTitleRequestDTO
from document_scrutiny.dtos.document_dtos import DocumentStateDTO, FieldValueDTO
from document_scrutiny.dtos.officer_action_dtos import UpdateDocumentFieldRequestDTO
from document_scrutiny.dtos.thread_dtos import (
    AddDocumentsToThreadDTO,
    CreateScrutinyThreadDTO,
    StoredFileDTO,
    UpdateDocumentDTO,
)

BUNDLE_APPLICATION_ID = "BN/2026/0455"


def bundle_named(filename: str):
    return next(spec for spec in BUNDLE_SPECS if spec.filename == filename)


class TestAnEditReachesTheChain:
    @pytest.fixture
    def storage(self):
        from document_scrutiny.storages.in_memory_scrutiny_thread_storage import (
            InMemoryScrutinyThreadStorage,
        )

        return InMemoryScrutinyThreadStorage()

    @pytest.fixture
    def edit_interactor(self, storage):
        from document_catalog.app_interfaces.catalog_service_interface import (
            CatalogServiceInterface,
        )
        from document_scrutiny.interactors.update_document_field_interactor import (
            UpdateDocumentFieldInteractor,
        )

        return UpdateDocumentFieldInteractor(
            thread_storage=storage,
            catalog_service=CatalogServiceInterface(),
            scrutiny_today="2026-09-07",
        )

    @pytest.fixture
    def chain_interactor(self, storage):
        from document_scrutiny.interactors.get_chain_of_title_interactor import (
            GetChainOfTitleInteractor,
        )

        return GetChainOfTitleInteractor(thread_storage=storage)

    def _seed_bundle(self, storage, filename: str):
        thread = storage.create_thread(
            create_thread=CreateScrutinyThreadDTO(
                application_id=BUNDLE_APPLICATION_ID
            )
        )
        bundle = bundle_named(filename)
        for index, deed in enumerate(bundle.deeds):
            added = storage.add_documents(
                add_documents=AddDocumentsToThreadDTO(
                    thread_id=thread.thread_id,
                    stored_files=(
                        StoredFileDTO(
                            filename=f"deed_{index}.pdf",
                            file_format="PDF",
                            file_size_bytes=1000,
                            stored_path=f"/tmp/deed_{index}.pdf",
                        ),
                    ),
                )
            )[0]
            storage.update_document(
                update_document=UpdateDocumentDTO(
                    thread_id=thread.thread_id,
                    document=self._as_read_document(added, deed),
                )
            )
        return thread.thread_id

    @staticmethod
    def _as_read_document(document: DocumentStateDTO, deed) -> DocumentStateDTO:
        import dataclasses

        record = deed.as_deed_record()
        field_values = tuple(
            FieldValueDTO(key=key, value=value, confidence=0.95)
            for key, value in deed.as_field_values().items()
        )
        return dataclasses.replace(
            document,
            document_type_id=deed.document_type_id,
            document_type_label="Sale deed",
            type_confidence=0.95,
            implemented=True,
            stage=DocumentStage.DONE.value,
            status=DocumentStatus.VERIFIED.value,
            field_values=field_values,
            deed_record=record,
            page_count=PAGES_PER_DEED,
        )

    def _current_deed_document_id(self, storage, thread_id: str) -> str:
        thread = storage.get_thread(thread_id=thread_id)
        return next(
            document.document_id
            for document in thread.documents
            if document.deed_record is not None
            and document.deed_record.doc_no == "5820/2019"
        )

    def test_correcting_the_stranger_to_the_true_prior_buyer_mends_the_chain(
        self, storage, edit_interactor, chain_interactor
    ):
        """Bundle 04's 2019 vendor is read as Mohammed Farooq, who never bought in.
        Correcting the vendor to Sunita Sharma — the 2011 buyer — should mend it."""
        # Arrange
        thread_id = self._seed_bundle(storage, BROKEN_STRANGER_SELLER_FILENAME)
        before = chain_interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=thread_id)
        )
        assert before.overall == ChainVerdict.BROKEN.value

        # Act
        edit_interactor.update_field(
            request=UpdateDocumentFieldRequestDTO(
                thread_id=thread_id,
                document_id=self._current_deed_document_id(storage, thread_id),
                field_key="vendor",
                value="Sunita Sharma",
            )
        )

        # Assert
        after = chain_interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=thread_id)
        )
        assert after.overall == ChainVerdict.INTACT.value
        assert [link.verdict for link in after.links] == [
            LinkVerdict.LINKED.value,
            LinkVerdict.LINKED.value,
        ]

    def test_correcting_the_extent_closes_the_gap(
        self, storage, edit_interactor, chain_interactor
    ):
        """Bundle 03's 2019 deed reads 600 sq.yd against 400 acquired. If that was a
        misread and the true extent is 400, correcting it should close the gap."""
        # Arrange
        thread_id = self._seed_bundle(storage, GAP_EXTENT_OVERFLOW_FILENAME)
        before = chain_interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=thread_id)
        )
        assert before.links[-1].verdict == LinkVerdict.GAP.value

        # Act
        edit_interactor.update_field(
            request=UpdateDocumentFieldRequestDTO(
                thread_id=thread_id,
                document_id=self._current_deed_document_id(storage, thread_id),
                field_key="extent",
                value="400 Sq. Yards (334.45 Sq. Metres)",
            )
        )

        # Assert
        after = chain_interactor.get_chain_of_title(
            request=ChainOfTitleRequestDTO(thread_id=thread_id)
        )
        assert after.overall == ChainVerdict.INTACT.value
        assert after.links[-1].verdict == LinkVerdict.LINKED.value

    def test_the_flat_value_the_officer_sees_is_also_updated(
        self, storage, edit_interactor
    ):
        # Arrange
        thread_id = self._seed_bundle(storage, BROKEN_STRANGER_SELLER_FILENAME)
        document_id = self._current_deed_document_id(storage, thread_id)

        # Act
        change = edit_interactor.update_field(
            request=UpdateDocumentFieldRequestDTO(
                thread_id=thread_id,
                document_id=document_id,
                field_key="vendor",
                value="Sunita Sharma",
            )
        )

        # Assert — both surfaces move together
        vendor_value = next(
            value for value in change.document.field_values if value.key == "vendor"
        )
        assert vendor_value.value == "Sunita Sharma"
        assert vendor_value.edited is True
        assert change.document.deed_record.sellers[0].name == "Sunita Sharma"
