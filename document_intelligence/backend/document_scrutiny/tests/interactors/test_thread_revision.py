import dataclasses

import pytest

from document_scrutiny.constants.enums import (
    CheckStatus,
    DocumentStage,
    DocumentStatus,
)
from document_scrutiny.tests.conftest import ScrutinyStorageMock, wire_document_memory
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    CheckDTOFactory,
    DocumentStateDTOFactory,
)

THREAD_ID = "thread_1"
DOCUMENT_ID = "document_1"


class TestThreadRevision(ScrutinyStorageMock):
    """The one place every officer action funnels its write through, so the
    document's own verdict cannot go stale behind a resolved check."""

    @pytest.fixture
    def revision(self, thread_storage):
        from document_scrutiny.interactors.thread_revision import ThreadRevision

        return ThreadRevision(thread_storage=thread_storage)

    def test_a_resolved_failure_no_longer_makes_the_document_read_failed(
        self, revision, thread_storage
    ):
        # Arrange
        failing = CheckDTOFactory(
            check_id=f"{DOCUMENT_ID}:pan",
            document_id=DOCUMENT_ID,
            status=CheckStatus.FAIL.value,
        )
        document = DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            stage=DocumentStage.DONE.value,
            status=DocumentStatus.FAILED.value,
            checks=(failing,),
        )
        wire_document_memory(thread_storage=thread_storage, documents=(document,))

        # Act
        saved, summary = revision.save_document(
            thread_id=THREAD_ID,
            document=dataclasses.replace(
                document,
                checks=(dataclasses.replace(failing, acknowledged=True),),
            ),
        )

        # Assert
        assert saved.status == DocumentStatus.VERIFIED.value
        assert summary.open_items == ()

    def test_the_persisted_document_carries_the_recomputed_verdict(
        self, revision, thread_storage
    ):
        # Arrange
        failing = CheckDTOFactory(
            check_id=f"{DOCUMENT_ID}:pan",
            document_id=DOCUMENT_ID,
            status=CheckStatus.FAIL.value,
        )
        document = DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            stage=DocumentStage.DONE.value,
            status=DocumentStatus.FAILED.value,
            checks=(failing,),
        )
        wire_document_memory(thread_storage=thread_storage, documents=(document,))

        # Act
        revision.save_document(
            thread_id=THREAD_ID,
            document=dataclasses.replace(
                document,
                checks=(dataclasses.replace(failing, acknowledged=True),),
            ),
        )

        # Assert
        written = thread_storage.update_document.call_args.kwargs["update_document"]
        assert written.document.status == DocumentStatus.VERIFIED.value

    def test_a_fresh_disagreement_makes_the_document_need_attention_again(
        self, revision, thread_storage
    ):
        # Arrange
        document = DocumentStateDTOFactory(
            document_id=DOCUMENT_ID,
            stage=DocumentStage.DONE.value,
            status=DocumentStatus.VERIFIED.value,
            checks=(),
        )
        wire_document_memory(thread_storage=thread_storage, documents=(document,))

        # Act
        saved, _ = revision.save_document(
            thread_id=THREAD_ID,
            document=dataclasses.replace(
                document,
                checks=(
                    CheckDTOFactory(
                        check_id=f"{DOCUMENT_ID}:issuer",
                        document_id=DOCUMENT_ID,
                        status=CheckStatus.WARN.value,
                    ),
                ),
            ),
        )

        # Assert
        assert saved.status == DocumentStatus.ATTENTION.value

    def test_the_stage_the_caller_set_is_left_alone(self, revision, thread_storage):
        # Arrange
        document = DocumentStateDTOFactory(
            document_id=DOCUMENT_ID, stage=DocumentStage.DONE.value
        )
        wire_document_memory(thread_storage=thread_storage, documents=(document,))

        # Act
        saved, _ = revision.save_document(thread_id=THREAD_ID, document=document)

        # Assert
        assert saved.stage == DocumentStage.DONE.value
