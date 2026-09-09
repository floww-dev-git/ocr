from document_catalog.storages.reference_data.document_type_specs import (
    DOCUMENT_TYPE_SPECS,
)
from document_scrutiny.constants.comparable_application_fields import (
    CHECK_KEYS_BY_APPLICATION_FIELD,
    ComparableApplicationField,
)


class TestComparableApplicationField:
    def test_every_comparable_field_is_one_the_catalog_actually_declares(self):
        # Arrange — app isolation means this app restates the application field
        # keys it can compare, so the two sides have to be pinned together. Every
        # type this build actually reads counts: a field one type compares against
        # and this app has never heard of would raise on the first document.
        declared_keys = {
            field_spec.application_field_key
            for document_type in DOCUMENT_TYPE_SPECS
            if document_type.implemented
            for field_spec in document_type.field_specs
            if field_spec.application_field_key is not None
        }

        # Act
        comparable_keys = {field.value for field in ComparableApplicationField}

        # Assert
        assert comparable_keys == declared_keys

    def test_every_comparable_field_has_a_check_key(self):
        # Arrange
        comparable_keys = {field.value for field in ComparableApplicationField}

        # Act
        mapped_keys = set(CHECK_KEYS_BY_APPLICATION_FIELD)

        # Assert
        assert mapped_keys == comparable_keys

    def test_the_check_keys_are_distinct(self):
        # Act
        check_keys = list(CHECK_KEYS_BY_APPLICATION_FIELD.values())

        # Assert
        assert len(check_keys) == len(set(check_keys))
