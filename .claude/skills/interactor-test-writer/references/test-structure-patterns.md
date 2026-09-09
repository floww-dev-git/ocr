# Test Structure Patterns Reference

## Complete Test File Example

```python
import pytest
from unittest.mock import create_autospec

from ib_collections.tests.interactors.storage_mock import StorageMock
from ib_collections.tests.factories.interactors.filter_dtos import (
    CreateFilterSetDTOFactory,
    UpdateConditionDTOFactory,
)
from ib_collections.tests.common_fixtures.interactors import (
    prepare_link_parent_with_ids_mock,
)


class TestFilterSetCrudInteractor(StorageMock):

    @pytest.fixture
    def interactor(self, filter_storage_mock):
        from ib_collections.interactors.filters.filter_set_crud_interactor import (
            FilterSetCrudInteractor,
        )
        return FilterSetCrudInteractor(
            filter_storage=filter_storage_mock,
        )

    # --- Error Cases First ---

    def test_update_filter_set_with_invalid_filter_set_id(
        self, interactor, filter_storage_mock
    ):
        # Arrange
        name = "Filter Set"
        filter_set_id = "filter_set_0"
        filter_storage_mock.get_valid_filter_set_ids.return_value = []

        # Act
        from ib_collections.exceptions.filter_exceptions import (
            InvalidFilterSetId,
        )

        with pytest.raises(InvalidFilterSetId) as err:
            interactor.update_filter_set_name(
                filter_set_id=filter_set_id, name=name
            )

        # Assert
        assert err.value.filter_set_id == filter_set_id
        filter_storage_mock.get_valid_filter_set_ids.assert_called_once_with(
            filter_set_ids=[filter_set_id]
        )
        filter_storage_mock.update_filter_set_name.assert_not_called()

    def test_create_filter_set_with_name_as_none(
        self, interactor, filter_storage_mock
    ):
        # Arrange
        name = None

        # Act
        from ib_collections.exceptions.filter_exceptions import (
            InvalidFilterSetName,
        )

        with pytest.raises(InvalidFilterSetName):
            interactor.create_filter_set(name=name)

        # Assert
        filter_storage_mock.create_filter_set.assert_not_called()

    # --- Success Cases Last ---

    def test_update_filter_set_name(
        self, interactor, filter_storage_mock
    ):
        # Arrange
        name = "Filter Set"
        filter_set_id = "filter_set_0"
        filter_storage_mock.get_valid_filter_set_ids.return_value = [
            filter_set_id
        ]

        # Act
        interactor.update_filter_set_name(
            filter_set_id=filter_set_id, name=name
        )

        # Assert
        filter_storage_mock.get_valid_filter_set_ids.assert_called_once_with(
            filter_set_ids=[filter_set_id]
        )
        filter_storage_mock.update_filter_set_name.assert_called_once_with(
            filter_set_id=filter_set_id, name=name
        )

    def test_create_filter_sets(
        self, interactor, filter_storage_mock
    ):
        # Arrange
        create_filter_set_dtos = CreateFilterSetDTOFactory.create_batch(
            size=2
        )

        # Act
        interactor.create_filter_sets(
            create_filter_set_dtos=create_filter_set_dtos
        )

        # Assert
        filter_storage_mock.create_filter_sets.assert_called_once_with(
            create_filter_set_dtos=create_filter_set_dtos
        )
```

## Test Class with Multiple Storage Dependencies

```python
class TestCreateCollectionInteractor(StorageMock):

    @pytest.fixture
    def interactor(
        self, collection_storage_mock, filter_storage_mock, view_storage_mock
    ):
        from ib_collections.interactors.collections.create_collection_interactor import (
            CreateCollectionInteractor,
        )
        return CreateCollectionInteractor(
            collection_storage=collection_storage_mock,
            filter_storage=filter_storage_mock,
            view_storage=view_storage_mock,
        )

    def test_create_collection_success(
        self, interactor, collection_storage_mock, filter_storage_mock, mocker
    ):
        # Arrange
        link_parent_mock = prepare_link_parent_with_ids_mock(mocker)
        link_parent_mock.return_value = (collection_dto, None, None)

        create_dto = CreateCollectionDTOFactory()
        collection_storage_mock.create_collection.return_value = "col_1"

        # Act
        result = interactor.create_collection(
            create_collection_dto=create_dto
        )

        # Assert
        collection_storage_mock.create_collection.assert_called_once()
        link_parent_mock.assert_called_once_with(
            collection_id="col_1",
            parent_id=create_dto.parent_collection_id,
        )
```

## Exception Testing Pattern

```python
def test_entity_not_found(self, interactor, storage_mock):
    # Arrange
    entity_id = "nonexistent_id"
    storage_mock.get_valid_entity_ids.return_value = []

    # Act
    from <app>.exceptions.<module> import EntityNotFoundException

    with pytest.raises(EntityNotFoundException) as err:
        interactor.process_entity(entity_id=entity_id)

    # Assert
    assert err.value.entity_id == entity_id
    storage_mock.get_valid_entity_ids.assert_called_once_with(
        entity_ids=[entity_id]
    )
    # Verify downstream calls were NOT made
    storage_mock.update_entity.assert_not_called()
```

## Parametrize Pattern

```python
@pytest.mark.parametrize("operator", Operator.empty_value_operators())
def test_with_empty_value_for_empty_operators(
    self, interactor, operator, filter_storage_mock
):
    # Arrange
    condition_dto = UpdateConditionDTOFactory(
        operator=operator, value=None
    )

    # Act
    interactor.validate_condition(condition_dto=condition_dto)

    # Assert
    filter_storage_mock.update_condition.assert_called_once()


@pytest.mark.parametrize(
    "operator, value",
    [
        (Operator.GTE.value, "1"),
        (Operator.LTE.value, [1, 2, 3]),
    ],
)
def test_with_different_operators(
    self, interactor, operator, value, filter_storage_mock
):
    # Arrange
    condition_dto = UpdateConditionDTOFactory(
        operator=operator, value=value
    )

    # Act
    result = interactor.validate_condition(condition_dto=condition_dto)

    # Assert
    assert result is True
```

## Test with mocker for Interactor Dependencies

```python
def test_with_interactor_dependency(self, interactor, mocker, storage_mock):
    # Arrange
    from <app>.tests.common_fixtures.interactors import (
        some_helper_interactor_mock,
    )

    helper_mock = some_helper_interactor_mock(mocker)
    helper_mock.return_value = expected_result

    input_dto = InputDTOFactory()
    storage_mock.get_data.return_value = data_dto

    # Act
    result = interactor.execute(input_dto=input_dto)

    # Assert
    storage_mock.get_data.assert_called_once_with(id=input_dto.id)
    helper_mock.assert_called_once_with(data=data_dto)
    assert result == expected_result
```

## No Private Helper Methods

**NEVER create private helper methods** (`_setup_*`, `_build_*`, `_create_*`) in test classes. They deviate from idiomatic pytest conventions and reduce readability.

### Instead of `_setup_*` helpers, use pytest fixtures:

```python
# BAD - private helper method
def _setup_validator_mock(self, mocker, field_type=FieldType.FILE_UPLOADER.value):
    field_dto = FieldDTOFactory(field_type=field_type)
    crm_entity_dto = CrmEntityDTOFactory()
    validate_crm_entity_and_field_access_mock(
        mocker,
        return_value=(crm_entity_dto, field_dto, False, False, crm_entity_dto),
    )

# GOOD - pytest fixture for the common/default case
@pytest.fixture
def setup_validator(self, mocker):
    field_dto = FieldDTOFactory(field_type=FieldType.FILE_UPLOADER.value)
    crm_entity_dto = CrmEntityDTOFactory()
    validate_crm_entity_and_field_access_mock(
        mocker,
        return_value=(crm_entity_dto, field_dto, False, False, crm_entity_dto),
    )

# Tests that need the default just include `setup_validator` in their parameter list.
# Tests that need a different value (e.g., PLAIN_TEXT) call the mock helper directly inline.
```

### Instead of `_build_*` helpers, use Factory Boy factories:

```python
# BAD - private helper that constructs DTOs
def _build_file_response_dto(self, file_id, url):
    return FileUploaderFieldResponseDTO(
        url_responses=[
            FileUploaderFieldUrlResponseDTO(
                file_id=file_id, name=f"{file_id}.pdf",
                mime_type="application/pdf", size_in_bytes=1000,
                url=url, is_document_url=False,
            ),
        ]
    )

# GOOD - Factory Boy factories for both outer and inner DTOs
# In factories file:
class FileUploaderFieldUrlResponseDTOFactory(factory.Factory):
    class Meta:
        model = FileUploaderFieldUrlResponseDTO
    file_id = factory.Sequence(lambda n: f"file_{n}")
    name = factory.Sequence(lambda n: f"file_{n}.pdf")
    mime_type = "application/pdf"
    size_in_bytes = 1000
    url = factory.Sequence(lambda n: f"https://s3.amazonaws.com/bucket/file_{n}.pdf")
    is_document_url = False


class FileUploaderFieldResponseDTOFactory(factory.Factory):
    class Meta:
        model = FileUploaderFieldResponseDTO

    @factory.lazy_attribute
    def url_responses(self):
        return FileUploaderFieldUrlResponseDTOFactory.create_batch(size=1)

# In tests:
response = FileUploaderFieldResponseDTOFactory(
    url_responses=[
        FileUploaderFieldUrlResponseDTOFactory(file_id="file_1", url="https://...")
    ]
)
```

## Test Naming Conventions

| Scenario | Naming Pattern |
|---|---|
| Invalid entity ID | `test_with_invalid_<entity>_id` |
| Entity not found | `test_<entity>_not_found` |
| Permission violation | `test_without_<permission>_permission` |
| Validation failure | `test_with_invalid_<field>` |
| Null/empty input | `test_with_<field>_as_none` |
| Business rule violation | `test_<rule_description>` |
| Success case | `test_<operation>_success` or `test_<operation>` |
| Success with specifics | `test_<operation>_with_<condition>` |

## Test Ordering Convention

1. Invalid input tests (None, empty, wrong type)
2. Entity not found tests (missing IDs)
3. Permission/authorization tests
4. Business rule violation tests
5. Edge case tests (boundary values, special conditions)
6. Success case tests (happy path)

## conftest.py Setup

```python
import pytest
from <app>.tests.factories.interactors import (
    filter_dtos,
    collection_dtos,
)


class InteractorDTOSResetSequenceSetup:
    def reset_sequence(self):
        self.filter_dtos()
        self.collection_dtos()

    @staticmethod
    def filter_dtos():
        filter_dtos.CreateFilterSetDTOFactory.reset_sequence(1, force=True)
        filter_dtos.UpdateConditionDTOFactory.reset_sequence(1, force=True)

    @staticmethod
    def collection_dtos():
        collection_dtos.CreateCollectionDTOFactory.reset_sequence(1, force=True)


@pytest.fixture(autouse=True, scope="function")
def reset_sequence():
    InteractorDTOSResetSequenceSetup().reset_sequence()
```

## Running Tests

```bash
# Run all tests in a file
pytest <app>/tests/interactors/<module>/test_<name>.py -v

# Run a specific test class
pytest <app>/tests/interactors/<module>/test_<name>.py::TestClassName -v

# Run a single test
pytest <app>/tests/interactors/<module>/test_<name>.py::TestClassName::test_method -v

# Run with output
pytest <app>/tests/interactors/<module>/test_<name>.py -v -s
```
