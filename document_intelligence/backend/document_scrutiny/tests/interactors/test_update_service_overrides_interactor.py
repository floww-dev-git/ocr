import pytest

from document_scrutiny.dtos.officer_action_dtos import UpdateServiceOverridesRequestDTO
from document_scrutiny.dtos.thread_dtos import ScrutinyThreadDTO
from document_scrutiny.exceptions.scrutiny_exceptions import ScrutinyThreadNotFound
from document_scrutiny.tests.conftest import MISMATCH_APPLICATION_ID, ScrutinyStorageMock
from document_verification.constants.verification_constants import ServiceOverride

THREAD_ID = "thread_1"
ISSUER_SERVICE_ID = "itd_pan"


class TestUpdateServiceOverridesInteractor(ScrutinyStorageMock):
    @pytest.fixture
    def interactor(self, thread_storage):
        from document_scrutiny.interactors.update_service_overrides_interactor import (
            UpdateServiceOverridesInteractor,
        )

        return UpdateServiceOverridesInteractor(thread_storage=thread_storage)

    @pytest.fixture(autouse=True)
    def _arrange(self, thread_storage):
        thread_storage.get_thread.return_value = ScrutinyThreadDTO(
            thread_id=THREAD_ID, application_id=MISMATCH_APPLICATION_ID
        )
        thread_storage.update_service_overrides.side_effect = (
            lambda update_overrides: ScrutinyThreadDTO(
                thread_id=update_overrides.thread_id,
                application_id=MISMATCH_APPLICATION_ID,
                service_overrides=dict(update_overrides.service_overrides),
            )
        )

    def _update(self, interactor, overrides):
        return interactor.update_overrides(
            request=UpdateServiceOverridesRequestDTO(
                thread_id=THREAD_ID, service_overrides=overrides
            )
        )

    def test_a_forced_answer_is_recorded_against_the_thread(self, interactor):
        # Act
        thread = self._update(
            interactor, {ISSUER_SERVICE_ID: ServiceOverride.TIMEOUT.value}
        )

        # Assert
        assert thread.service_overrides == {
            ISSUER_SERVICE_ID: ServiceOverride.TIMEOUT.value
        }

    def test_clearing_the_overrides_returns_the_thread_to_normal_service(
        self, interactor
    ):
        # Act
        thread = self._update(interactor, {})

        # Assert
        assert thread.service_overrides == {}

    def test_overrides_for_a_thread_that_does_not_exist_are_refused(
        self, interactor, thread_storage
    ):
        # Arrange
        thread_storage.get_thread.side_effect = ScrutinyThreadNotFound(
            thread_id=THREAD_ID
        )

        # Act & Assert
        with pytest.raises(ScrutinyThreadNotFound):
            self._update(
                interactor, {ISSUER_SERVICE_ID: ServiceOverride.TIMEOUT.value}
            )

        thread_storage.update_service_overrides.assert_not_called()
