import pytest

from document_catalog.constants.enums import ApplicationFieldGroup, ApplicationFieldKey
from document_catalog.exceptions.catalog_exceptions import ApplicationNotFound

EXPECTED_APPLICATION_COUNT = 6
EXPECTED_APPLICATION_FIELD_COUNT = 20
MISMATCH_APPLICATION_ID = "BN/2026/0377"
BUNDLE_APPLICATION_ID = "BN/2026/0455"
CLEAN_PATH_APPLICATION_ID = "BN/2026/0512"
AADHAAR_SHOWCASE_APPLICATION_ID = "BN/2026/0601"


class TestInMemoryApplicationStorage:
    @pytest.fixture
    def storage(self):
        from document_catalog.storages.in_memory_application_storage import (
            InMemoryApplicationStorage,
        )

        return InMemoryApplicationStorage()

    def test_get_application_with_unknown_id_raises_application_not_found(self, storage):
        # Arrange
        unknown_application_id = "BN/2026/9999"

        # Act & Assert
        with pytest.raises(ApplicationNotFound) as exception_info:
            storage.get_application(application_id=unknown_application_id)
        assert exception_info.value.application_id == unknown_application_id

    def test_get_applications_returns_every_prototype_application(self, storage):
        # Act
        applications = storage.get_applications()

        # Assert
        assert len(applications) == EXPECTED_APPLICATION_COUNT
        assert [application.application_id for application in applications] == [
            "BN/2026/0421",
            "BN/2026/0398",
            MISMATCH_APPLICATION_ID,
            BUNDLE_APPLICATION_ID,
            CLEAN_PATH_APPLICATION_ID,
            AADHAAR_SHOWCASE_APPLICATION_ID,
        ]

    def test_every_application_carries_every_declared_application_field(self, storage):
        # Arrange
        declared_field_keys = {
            field_spec.key for field_spec in storage.get_application_field_specs()
        }

        # Act
        applications = storage.get_applications()

        # Assert
        for application in applications:
            assert set(application.field_values.keys()) == declared_field_keys

    def test_get_application_field_specs_covers_all_three_prototype_groups(self, storage):
        # Act
        field_specs = storage.get_application_field_specs()

        # Assert
        assert len(field_specs) == EXPECTED_APPLICATION_FIELD_COUNT
        assert {field_spec.group for field_spec in field_specs} == {
            ApplicationFieldGroup.APPLICANT.value,
            ApplicationFieldGroup.PLOT.value,
            ApplicationFieldGroup.PROPOSAL.value,
        }

    def test_get_application_for_the_mismatch_case_carries_the_full_applicant_name(
        self, storage
    ):
        # Act
        application = storage.get_application(application_id=MISMATCH_APPLICATION_ID)

        # Assert
        field_values = application.field_values
        assert field_values[ApplicationFieldKey.APPLICANT_NAME.value] == (
            "Mohammed Irfan Siddiqui"
        )
        assert field_values[ApplicationFieldKey.PARENT_NAME.value] == (
            "Mohammed Yousuf Siddiqui"
        )
        assert field_values[ApplicationFieldKey.DATE_OF_BIRTH.value] == "1982-11-27"
        assert field_values[ApplicationFieldKey.PAN.value] == "BNMPS7720K"

    def test_get_application_returns_field_values_the_caller_cannot_mutate(self, storage):
        # Arrange
        application = storage.get_application(application_id=MISMATCH_APPLICATION_ID)

        # Act
        application.field_values[ApplicationFieldKey.APPLICANT_NAME.value] = "Tampered"

        # Assert
        untouched = storage.get_application(application_id=MISMATCH_APPLICATION_ID)
        assert untouched.field_values[ApplicationFieldKey.APPLICANT_NAME.value] == (
            "Mohammed Irfan Siddiqui"
        )
