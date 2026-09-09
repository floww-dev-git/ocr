# Action Generation Patterns

## GenerateActionsInteractor

**File**: `bps/configio/core/io_engine/generate_actions_interactor.py`

Iterates entity types, resolves the registered action generator, and collects all `ChangeConfigActionDTO` actions.

```python
class GenerateActionsInteractor:
    def __init__(self, entity_types, data_store, json_comparison_service):
        self._entity_types = entity_types  # List[GenerateEntityActionEnum]
        self._data_store = data_store
        self._json_comparison_service = json_comparison_service

    def generate_actions(self, old_config, new_config) -> GenerateActionsResultDTO:
        all_actions = []
        for entity_type in self._entity_types:
            generator_class = ActionGeneratorRegistry.get_generator_class(entity_type)
            generator = generator_class(
                json_comparison_service=self._json_comparison_service,
                data_store=self._data_store,
            )
            entity_actions = generator.generate_actions(old_config, new_config)
            all_actions.extend(entity_actions)
        return self._build_result(all_actions)
```

### How It's Called

From `ImportInteractor._create_change_actions()`:

```python
old_config = self._import_store.get_existing_config(data_store=data_store)
interactor = GenerateActionsInteractor(
    entity_types=self._import_store.generate_action_entity_types(),
    data_store=data_store,
    json_comparison_service=JsonComparisonService(),
)
result = interactor.generate_actions(old_config=old_config, new_config=new_config)
```

---

## ActionGeneratorRegistry

**File**: `bps/configio/core/generate_actions_utils/action_generator_registry.py`

Maps `GenerateEntityActionEnum` -> generator class via decorator.

```python
class ActionGeneratorRegistry:
    _registry: Dict[GenerateEntityActionEnum, Type[BaseEntityActionGenerator]] = {}

    @classmethod
    def register(cls, entity_type: GenerateEntityActionEnum):
        def decorator(generator_class):
            cls._registry[entity_type] = generator_class
            return generator_class
        return decorator

    @classmethod
    def get_generator_class(cls, entity_type):
        generator_class = cls._registry.get(entity_type)
        if not generator_class:
            raise UnsupportedEntityTypeError(
                f"No action generator registered for {entity_type.value}"
            )
        return generator_class

register_action_generator = ActionGeneratorRegistry.register
```

### Usage

```python
from bps.configio.core.generate_actions_utils.action_generator_registry import (
    register_action_generator,
)

@register_action_generator(GenerateEntityActionEnum.TDR_ACCOUNT)
class GenerateActionsForTdrAccountInteractor(BulkEntityActionGenerator):
    ...
```

---

## BaseEntityActionGenerator

**File**: `bps/configio/core/generate_actions_utils/base_entity_action_generator.py`

Abstract base class with 3 abstract properties and 2 abstract methods:

### Abstract Properties

| Property | Type | Purpose |
|----------|------|---------|
| `entity_type` | `GenerateEntityActionEnum` | The entity type this generator handles |
| `entity_id_field` | `str` | JSON key used as the entity's unique identifier |
| `config_key` | `str` | Top-level key in the config dict (e.g., `"tdr_certificates"`) |

### Abstract Methods

| Method | Purpose |
|--------|---------|
| `generate_actions(existing_config, incoming_config)` | Compare old vs new, emit actions |
| `build_entity_dto(entity_data)` | Convert JSON dict -> typed DTO |

### Helper Methods (inherited)

```python
def _build_create_action(self, entity_id, entity_data) -> ChangeConfigActionDTO:
    return ChangeConfigActionDTO(
        entity_id=entity_id,
        entity_type=self.entity_type,
        action=ConfigChangeActionEnum.CREATE,
        changes=[],
        entity_dto=self.build_entity_dto(entity_data),
    )

def _build_update_action(self, entity_id, field_changes, entity_data) -> ChangeConfigActionDTO:
    return ChangeConfigActionDTO(
        entity_id=entity_id,
        entity_type=self.entity_type,
        action=ConfigChangeActionEnum.UPDATE,
        changes=field_changes,
        entity_dto=self.build_entity_dto(entity_data),
    )

def _detect_field_changes(self, existing_entity, incoming_entity) -> List[ConfigChangeDTO]:
    comparison_result = self._json_comparison_service.compare(
        existing_entity, incoming_entity
    )
    if not comparison_result.has_changes:
        return []
    return [
        ConfigChangeDTO(key=change.field_key, old_value=change.old_value, new_value=change.new_value)
        for change in comparison_result.changed_fields
        if change.old_value != change.new_value
    ]
```

---

## Generator Subclasses

### BulkEntityActionGenerator (for collections of entities)

**File**: `bps/configio/core/generate_actions_utils/bulk_entity_action_generator.py`

For entities that have multiple records (e.g., accounts, transactions, stages).

```python
class BulkEntityActionGenerator(BaseEntityActionGenerator, abc.ABC):
    def generate_actions(self, existing_config, incoming_config):
        incoming_entities = incoming_config.get(self.config_key, [])
        existing_entities = self._extract_existing_entities(existing_config)

        if not existing_entities:
            return self._generate_create_actions_for_all(incoming_entities)

        return self._generate_actions_by_comparing_collections(
            existing_entities, incoming_entities
        )
```

Comparison logic:
- **New entities** (`incoming_ids - existing_ids`) -> CREATE actions
- **Common entities** (`incoming_ids & existing_ids`) -> UPDATE actions (if changed)
- Uses `entity_id_field` to match entities between old and new configs

### SingularEntityActionGenerator (for single-record entities)

**File**: `bps/configio/core/generate_actions_utils/singular_entity_action_generator.py`

For entities that have exactly one record (e.g., template config).

```python
class SingularEntityActionGenerator(BaseEntityActionGenerator, abc.ABC):
    def generate_actions(self, existing_config, incoming_config):
        incoming_entity = incoming_config.get(self.config_key)
        if not incoming_entity:
            return []
        existing_entity = self._extract_existing_entity(existing_config)
        if existing_entity is None:
            return [self._build_create_action(
                entity_id=incoming_entity[self.entity_id_field],
                entity_data=incoming_entity,
            )]
        return self._generate_update_action_if_changed(existing_entity, incoming_entity)
```

---

## ChangeConfigActionDTO Structure

**File**: `bps/configio/bps_template/dtos.py`

```python
@dataclass
class ChangeConfigActionDTO:
    entity_id: str                              # Unique identifier for this entity
    entity_type: GenerateEntityActionEnum        # Which entity type
    action: ConfigChangeActionEnum               # CREATE / UPDATE / DELETE
    changes: List[ConfigChangeDTO]               # List of field-level changes
    entity_dto: Union[...] = None                # Typed DTO for the entity

@dataclass
class ConfigChangeDTO:
    key: str                # JSON key that changed
    old_value: Optional[str]  # Previous value
    new_value: Optional[str]  # New value
```

---

## `build_entity_dto()` Pattern

This is the **reverse of export's `convert_dto_to_json()`**.

| Direction | Method | Conversion |
|-----------|--------|-----------|
| Export | `convert_dto_to_json()` | DTO fields -> JSON key-value pairs |
| Import | `build_entity_dto()` | JSON key-value pairs -> typed DTO |

### Example

```python
# In action generator:
def build_entity_dto(self, entity_data: Dict[str, Any]) -> TDRAccountDTO:
    return self.tdr_adapter.convert_account_json_to_dto(
        account_json=entity_data, data_store=self.data_store
    )
```

The adapter method maps JSON keys back to DTO fields, resolving lookups (e.g., authority string -> bank_id, account_no -> account_id).

---

## Registration Side-Effect Pattern

Action generators use decorators for registration. **The module must be imported** for the decorator to execute.

### `__init__.py` Triggers Registration

**File**: `bps/configio/tdr_bank/action_generators/__init__.py`

```python
from .generate_actions_for_tdr_account import GenerateActionsForTdrAccountInteractor
from .generate_actions_for_tdr_account_transaction import (
    GenerateActionsForTdrAccountTransactionInteractor,
)
from .generate_actions_for_tdr_account_transaction_log import (
    GenerateActionsForTdrAccountTransactionLogInteractor,
)
from .generate_actions_for_pipeline_item_remarks import (
    GenerateActionsForPipelineItemRemarksInteractor,
)
```

### ImportStore Must Import the Package

```python
# At the top of import_store.py
import bps.configio.tdr_bank.action_generators  # noqa: F401
```

Without this import, `ActionGeneratorRegistry.get_generator_class()` will raise `UnsupportedEntityTypeError`.

---

## GenerateActionsResultDTO

**File**: `bps/configio/bps_template/dtos.py`

```python
@dataclass
class GenerateActionsResultDTO:
    actions: List[ChangeConfigActionDTO]
    actions_by_entity: Dict[GenerateEntityActionEnum, int]
    actions_by_type: Dict[ConfigChangeActionEnum, int]
    total_actions: int
```

---

## Complete Action Generator Example

```python
from bps.configio.bps_template.constants.action_enums import GenerateEntityActionEnum
from bps.configio.core.generate_actions_utils.action_generator_registry import (
    register_action_generator,
)
from bps.configio.core.generate_actions_utils.bulk_entity_action_generator import (
    BulkEntityActionGenerator,
)


@register_action_generator(GenerateEntityActionEnum.TDR_ACCOUNT)
class GenerateActionsForTdrAccountInteractor(BulkEntityActionGenerator):
    @property
    def entity_type(self) -> GenerateEntityActionEnum:
        return GenerateEntityActionEnum.TDR_ACCOUNT

    @property
    def entity_id_field(self) -> str:
        return AccountJsonKeys.TDR_CERTIFICATE_NO.value

    @property
    def config_key(self) -> str:
        return TDRBankJsonKeys.ACCOUNTS.value

    def build_entity_dto(self, entity_data):
        return self.tdr_adapter.convert_account_json_to_dto(
            account_json=entity_data, data_store=self.data_store
        )
```

- Extends `BulkEntityActionGenerator` (multiple accounts)
- `entity_id_field` = the JSON key used as unique ID (`tdr_certificate_no`)
- `config_key` = top-level key in config dict (`tdr_certificates`)
- `build_entity_dto()` converts JSON back to `TDRAccountDTO`
