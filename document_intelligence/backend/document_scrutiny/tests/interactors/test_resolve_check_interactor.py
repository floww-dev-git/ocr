import pytest

from document_scrutiny.constants.enums import (
    CheckGroup,
    CheckResolution,
    CheckStatus,
    ThreadStatus,
)
from document_scrutiny.dtos.officer_action_dtos import ResolveCheckRequestDTO
from document_scrutiny.exceptions.scrutiny_exceptions import (
    CheckNotFound,
    UnknownCheckResolution,
)
from document_scrutiny.tests.conftest import ScrutinyStorageMock, wire_document_memory
from document_scrutiny.tests.factories.scrutiny_dto_factories import (
    CheckDTOFactory,
    DocumentStateDTOFactory,
)

THREAD_ID = "thread_1"
DOCUMENT_ID = "document_1"
WARNING_CHECK_ID = f"{DOCUMENT_ID}:issuer"
WARNING_TITLE = "Income Tax PAN verification did not fully match"


class TestResolveCheckInteractor(ScrutinyStorageMock):
    @pytest.fixture
    def interactor(self, thread_storage):
        from document_scrutiny.interactors.resolve_check_interactor import (
            ResolveCheckInteractor,
        )

        return ResolveCheckInteractor(thread_storage=thread_storage)

    @pytest.fixture
    def warning_check(self):
        return CheckDTOFactory(
            check_id=WARNING_CHECK_ID,
            document_id=DOCUMENT_ID,
            group=CheckGroup.EXTERNAL.value,
            status=CheckStatus.WARN.value,
            title=WARNING_TITLE,
        )

    @pytest.fixture(autouse=True)
    def _arrange(self, thread_storage, warning_check):
        wire_document_memory(
            thread_storage=thread_storage,
            documents=(
                DocumentStateDTOFactory(
                    document_id=DOCUMENT_ID, checks=(warning_check,)
                ),
            ),
        )

    def _resolve(
        self,
        interactor,
        action: str = CheckResolution.ACKNOWLEDGED.value,
        check_id: str = WARNING_CHECK_ID,
    ):
        return interactor.resolve_check(
            request=ResolveCheckRequestDTO(
                thread_id=THREAD_ID, check_id=check_id, action=action
            )
        )

    def test_acknowledging_a_warning_records_the_officer_saw_it(self, interactor):
        # Act
        change = self._resolve(interactor)

        # Assert
        assert change.check.acknowledged is True

    def test_marking_a_check_verified_by_hand_records_that_choice(self, interactor):
        # Act
        change = self._resolve(interactor, action=CheckResolution.MANUAL.value)

        # Assert
        assert change.check.manual is True

    def test_requesting_a_document_from_the_applicant_records_that_choice(
        self, interactor
    ):
        # Act
        change = self._resolve(interactor, action=CheckResolution.REQUESTED.value)

        # Assert
        assert change.check.requested is True

    def test_the_officers_disposition_never_rewrites_the_machines_verdict(
        self, interactor
    ):
        # Act
        change = self._resolve(interactor, action=CheckResolution.MANUAL.value)

        # Assert
        assert change.check.status == CheckStatus.WARN.value
        assert change.check.title == WARNING_TITLE

    def test_an_acknowledged_warning_stops_holding_the_thread_open(self, interactor):
        # Act
        change = self._resolve(interactor)

        # Assert
        assert change.summary.open_items == ()
        assert change.summary.thread_status == ThreadStatus.CLEAR.value

    def test_a_check_still_awaiting_action_keeps_the_thread_in_attention(
        self, interactor
    ):
        # Act
        change = self._resolve(interactor, action=CheckResolution.REQUESTED.value)

        # Assert
        assert change.summary.thread_status == ThreadStatus.ATTENTION.value

    def test_acknowledging_twice_changes_nothing_further(self, interactor):
        # Act
        first = self._resolve(interactor)
        second = self._resolve(interactor)

        # Assert
        assert first.check == second.check

    def test_a_check_this_thread_does_not_have_cannot_be_resolved(
        self, interactor, thread_storage
    ):
        # Act & Assert
        with pytest.raises(CheckNotFound) as raised:
            self._resolve(interactor, check_id="document_9:name")

        assert raised.value.check_id == "document_9:name"
        thread_storage.update_document.assert_not_called()

    def test_an_action_the_system_does_not_offer_is_refused(
        self, interactor, thread_storage
    ):
        # Act & Assert
        with pytest.raises(UnknownCheckResolution) as raised:
            self._resolve(interactor, action="waived")

        assert raised.value.action == "waived"
        thread_storage.update_document.assert_not_called()

    def test_an_unknown_action_is_refused_before_the_thread_is_even_read(
        self, interactor, thread_storage
    ):
        # Act & Assert
        with pytest.raises(UnknownCheckResolution):
            self._resolve(interactor, action="waived")

        thread_storage.get_thread.assert_not_called()
