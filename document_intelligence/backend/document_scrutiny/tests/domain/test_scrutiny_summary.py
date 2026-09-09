from document_scrutiny.constants.enums import (
    CheckStatus,
    DocumentStage,
    DocumentStatus,
    ThreadStatus,
)
from document_scrutiny.domain.scrutiny_summary import ScrutinySummary
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    CheckDTOFactory,
    DocumentStateDTOFactory,
)


class TestScrutinySummary:
    def test_a_thread_with_no_documents_is_new(self):
        # Act
        summary = ScrutinySummary.summarise(documents=())

        # Assert
        assert summary.thread_status == ThreadStatus.NEW.value
        assert summary.document_count == 0
        assert summary.open_items == ()

    def test_a_thread_with_a_document_still_being_read_is_running(self):
        # Arrange
        documents = (
            DocumentStateDTOFactory(
                stage=DocumentStage.EXTRACTING.value,
                status=DocumentStatus.CHECKING.value,
            ),
        )

        # Act
        summary = ScrutinySummary.summarise(documents=documents)

        # Assert
        assert summary.thread_status == ThreadStatus.RUNNING.value

    def test_an_open_warning_puts_the_thread_in_attention(self):
        # Arrange
        documents = (
            DocumentStateDTOFactory(
                document_id="document_1",
                checks=(
                    CheckDTOFactory(
                        check_id="document_1:name",
                        document_id="document_1",
                        status=CheckStatus.WARN.value,
                        title="Name matches application",
                    ),
                ),
            ),
        )

        # Act
        summary = ScrutinySummary.summarise(documents=documents)

        # Assert
        assert summary.thread_status == ThreadStatus.ATTENTION.value
        assert len(summary.open_items) == 1
        assert summary.open_items[0].text == "PAN: Name matches application"
        assert summary.open_items[0].check_id == "document_1:name"
        assert summary.open_items[0].document_id == "document_1"

    def test_an_acknowledged_warning_lets_the_thread_reach_clear(self):
        # Arrange — AC9
        documents = (
            DocumentStateDTOFactory(
                checks=(
                    CheckDTOFactory(status=CheckStatus.WARN.value, acknowledged=True),
                ),
            ),
        )

        # Act
        summary = ScrutinySummary.summarise(documents=documents)

        # Assert
        assert summary.thread_status == ThreadStatus.CLEAR.value
        assert summary.open_items == ()

    def test_counts_every_check_status_across_every_document(self):
        # Arrange
        documents = (
            DocumentStateDTOFactory(
                checks=(
                    CheckDTOFactory(status=CheckStatus.PASS.value),
                    CheckDTOFactory(status=CheckStatus.PASS.value),
                    CheckDTOFactory(status=CheckStatus.WARN.value),
                ),
            ),
            DocumentStateDTOFactory(
                checks=(
                    CheckDTOFactory(status=CheckStatus.PASS.value),
                    CheckDTOFactory(status=CheckStatus.FAIL.value),
                    CheckDTOFactory(status=CheckStatus.UNAVAILABLE.value),
                    CheckDTOFactory(status=CheckStatus.INFO.value),
                ),
            ),
        )

        # Act
        summary = ScrutinySummary.summarise(documents=documents)

        # Assert
        assert summary.status_counts == {
            CheckStatus.PASS.value: 3,
            CheckStatus.WARN.value: 1,
            CheckStatus.FAIL.value: 1,
            CheckStatus.UNAVAILABLE.value: 1,
            CheckStatus.INFO.value: 1,
            CheckStatus.PENDING.value: 0,
        }
        assert summary.document_count == 2

    def test_counts_the_documents_whose_fields_the_officer_confirmed(self):
        # Arrange
        documents = (
            DocumentStateDTOFactory(confirmed=True),
            DocumentStateDTOFactory(confirmed=False),
            DocumentStateDTOFactory(confirmed=True),
        )

        # Act
        summary = ScrutinySummary.summarise(documents=documents)

        # Assert
        assert summary.confirmed_document_count == 2

    def test_a_thread_whose_every_check_passes_is_clear(self):
        # Arrange — AC1
        documents = (
            DocumentStateDTOFactory(
                checks=(CheckDTOFactory(status=CheckStatus.PASS.value),) * 8
            ),
        )

        # Act
        summary = ScrutinySummary.summarise(documents=documents)

        # Assert
        assert summary.thread_status == ThreadStatus.CLEAR.value
        assert summary.status_counts[CheckStatus.PASS.value] == 8
        assert summary.open_items == ()

    def test_open_items_are_listed_document_by_document_in_order(self):
        # Arrange
        documents = (
            DocumentStateDTOFactory(
                document_id="document_1",
                document_type_label="PAN",
                checks=(
                    CheckDTOFactory(
                        check_id="document_1:pan-format",
                        document_id="document_1",
                        status=CheckStatus.FAIL.value,
                        title="PAN is not a valid PAN",
                    ),
                ),
            ),
            DocumentStateDTOFactory(
                document_id="document_2",
                document_type_label="Aadhaar",
                checks=(
                    CheckDTOFactory(
                        check_id="document_2:name",
                        document_id="document_2",
                        status=CheckStatus.WARN.value,
                        title="Name matches application",
                    ),
                ),
            ),
        )

        # Act
        summary = ScrutinySummary.summarise(documents=documents)

        # Assert
        assert [item.text for item in summary.open_items] == [
            "PAN: PAN is not a valid PAN",
            "Aadhaar: Name matches application",
        ]
