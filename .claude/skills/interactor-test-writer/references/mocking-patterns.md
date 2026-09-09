# Mocking Patterns Reference

## Storage Interface Mocking

### StorageMock Base Class

Located at: `<app>/tests/interactors/storage_mock.py`

Every storage mock uses `create_autospec()` which auto-validates method signatures.

```python
from unittest.mock import create_autospec
import pytest


class StorageMock:
    @pytest.fixture
    def filter_storage_mock(self):
        from ib_collections.interactors.storage_interfaces.filter_storage_interface import (
            FilterStorageInterface,
        )
        return create_autospec(FilterStorageInterface)

    @pytest.fixture
    def collection_storage_mock(self):
        from ib_collections.interactors.storage_interfaces.collection_storage_interface import (
            CollectionStorageInterface,
        )
        return create_autospec(CollectionStorageInterface)
```

**Rules:**
- Always use `create_autospec(<InterfaceClass>)` - never `MagicMock()` or `Mock()`
- Import storage interfaces INSIDE the fixture (lazy imports)
- One fixture per storage interface
- Fixture name convention: `<descriptive_name>_storage_mock` or `<descriptive_name>_storage`

### No MagicMock

- Do NOT use `MagicMock()` for DTOs or stub objects — create a Factory Boy factory instead
- Use `create_autospec()` for storage interfaces and adapters (already covered above)
- If a test needs an object with only one attribute (e.g., `field_type`), create a minimal DTO factory with that field

### Configuring Mock Return Values

```python
# Single return value
storage_mock.get_entity.return_value = EntityDTOFactory()

# Return a list
storage_mock.get_valid_ids.return_value = ["id_1", "id_2"]

# Return None (entity not found)
storage_mock.get_entity.return_value = None

# Raise an exception
storage_mock.get_entity.side_effect = EntityNotFoundError("id_1")

# Different returns on successive calls
storage_mock.get_entity.side_effect = [dto_1, dto_2, EntityNotFoundError()]
```

### Asserting Mock Calls

**ALWAYS use `assert_called_once_with()` with exact kwargs for call verification.**

**NEVER use `mock.call_args` to manually extract and verify arguments** — it is fragile, non-standard, and hard to read. If the mock was called with the wrong args, `assert_called_once_with()` gives a clear diff.

```python
# ✅ CORRECT - Called exactly once with specific args
storage_mock.create_entity.assert_called_once_with(
    name="Test", entity_id="id_1"
)

# ✅ CORRECT - Called once with no arg checking
storage_mock.create_entity.assert_called_once()

# ✅ CORRECT - Never called (for error paths that exit early)
storage_mock.create_entity.assert_not_called()

# ✅ CORRECT - Called multiple times
from unittest.mock import call
storage_mock.update_entity.assert_has_calls([
    call(entity_id="id_1", name="Name 1"),
    call(entity_id="id_2", name="Name 2"),
])

# ✅ CORRECT - Check call count
assert storage_mock.process.call_count == 3

# ❌ FORBIDDEN - Never parse call_args manually
mock.assert_called_once()
call_kwargs = mock.call_args
assert call_kwargs.kwargs.get("param") == expected  # DON'T DO THIS
```

## Interactor-to-Interactor Mocking

### The get_mock Helper

Located at: `<app>/tests/common_fixtures/__init__.py`

```python
def get_mock(mocker, func_to_mock):
    mock = mocker.patch(
        "{}.{}".format(func_to_mock.__module__, func_to_mock.__qualname__)
    )
    return mock
```

### Creating Interactor Mock Helpers

Located at: `<app>/tests/common_fixtures/interactors.py`

```python
from <app>.tests.common_fixtures import get_mock


def prepare_link_parent_with_ids_mock(mocker):
    from ib_collections.interactors.collections.link_parent_interactor import (
        LinkParentInteractor,
    )
    func_to_mock = LinkParentInteractor.link_parent_with_ids
    return get_mock(mocker=mocker, func_to_mock=func_to_mock)


def create_filter_set_mock(mocker):
    from ib_collections.interactors.filters.filter_set_crud_interactor import (
        FilterSetCrudInteractor,
    )
    func_to_mock = FilterSetCrudInteractor.create_filter_set
    return get_mock(mocker=mocker, func_to_mock=func_to_mock)
```

### Using Interactor Mocks in Tests

```python
from <app>.tests.common_fixtures.interactors import (
    prepare_link_parent_with_ids_mock,
    create_filter_set_mock,
)


def test_create_collection(self, interactor, mocker):
    # Arrange
    link_parent_mock = prepare_link_parent_with_ids_mock(mocker)
    link_parent_mock.return_value = (collection_dto, None, None)

    filter_set_mock = create_filter_set_mock(mocker)
    filter_set_mock.return_value = "filter_set_0"

    # Act
    interactor.create_collection(create_collection_dto=dto)

    # Assert
    link_parent_mock.assert_called_once_with(
        collection_id=collection_id,
        parent_id=dto.parent_collection_id,
    )
    filter_set_mock.assert_called_once_with(name=dto.filter_set_name)
```

## Cross-App Adapter Mocking

### Adapter Mock Helpers

Located at: `<app>/tests/common_fixtures/adapters/<service_name>.py`

```python
from <app>.tests.common_fixtures import get_mock


def get_pipeline_account_id_mock(mocker, return_value=None):
    from iam.app_interfaces.iam_interface import IamInterface
    func_to_mock = IamInterface.get_pipeline_account_id
    mock = get_mock(mocker=mocker, func_to_mock=func_to_mock)
    if return_value is not None:
        mock.return_value = return_value
    return mock


def validate_account_admin_mock(mocker, return_value=None):
    from iam.app_interfaces.iam_interface import IamInterface
    func_to_mock = IamInterface.validate_account_admin
    mock = get_mock(mocker=mocker, func_to_mock=func_to_mock)
    if return_value is not None:
        mock.return_value = return_value
    return mock
```

### Using Adapter Mocks in Tests

```python
from <app>.tests.common_fixtures.adapters.iam_service import (
    get_pipeline_account_id_mock,
    validate_account_admin_mock,
)


def test_with_admin_access(self, interactor, mocker):
    # Arrange
    get_pipeline_account_id_mock(mocker, return_value="account_123")
    validate_account_admin_mock(mocker, return_value=True)

    # Act
    result = interactor.perform_admin_action(user_id="user_1")

    # Assert
    assert result.success is True
```

## UUID Mocking

Located at: `<app>/tests/common_fixtures/common.py`

```python
def get_uuid_mock(mocker, return_value=None, side_effect=None):
    uuid_mock = mocker.patch("uuid.uuid4")
    if return_value is not None:
        uuid_mock.return_value = return_value
    if side_effect is not None:
        uuid_mock.side_effect = side_effect
    return uuid_mock
```

### Usage

```python
from <app>.tests.common_fixtures.common import get_uuid_mock


def test_entity_creation_with_uuid(self, interactor, mocker):
    # Arrange
    expected_id = "generated-uuid-123"
    get_uuid_mock(mocker, return_value=expected_id)

    # Act
    result = interactor.create_entity(name="Test")

    # Assert
    assert result.entity_id == expected_id
```

## Mixin Mocking

For interactors that use mixins (e.g., `IamMixin`, `ValidationMixin`), mock the mixin methods the same way as interactor methods:

```python
def validate_user_permission_mock(mocker):
    from <app>.interactors.mixins.iam_mixin import IamMixin
    func_to_mock = IamMixin.validate_user_permission
    return get_mock(mocker=mocker, func_to_mock=func_to_mock)
```
