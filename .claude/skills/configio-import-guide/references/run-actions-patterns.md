# Run Actions Patterns

## RunActionsOrchestrator

**File**: `bps/configio/bps_template/run_actions_handlers/run_actions.py`

Implements the **all-or-nothing** pattern: validates all actions first, executes only if all pass.

```python
class RunActionsOrchestrator:
    def __init__(self, data_store):
        self._data_store = data_store

    def run_all_checks(self, actions: List[ChangeConfigActionDTO]) -> List[RunActionErrorDTO]:
        errors = []
        for action in actions:
            handler_class = BPSTemplateRunActionRegistry.get_handler(
                entity_type=action.entity_type,
                action_type=action.action,
            )
            if not handler_class:
                errors.append(RunActionErrorDTO(
                    error_code=RunActionErrorCodeEnum.NO_HANDLER_FOUND,
                    message=f"No handler for {action.entity_type.value}:{action.action.value}",
                    action=action,
                ))
                continue
            handler = handler_class(data_store=self._data_store)
            action_errors = handler.run_check(action=action)
            errors.extend(action_errors)
        return errors

    def execute_all(self, actions: List[ChangeConfigActionDTO]) -> None:
        for action in actions:
            handler_class = BPSTemplateRunActionRegistry.get_handler(
                entity_type=action.entity_type,
                action_type=action.action,
            )
            if handler_class:
                handler = handler_class(data_store=self._data_store)
                handler.execute(action=action)

    def validate_and_execute(self, actions):
        errors = self.run_all_checks(actions=actions)
        if errors:
            return errors, False
        self.execute_all(actions=actions)
        return [], True
```

### How It's Called

From `ImportInteractor._execute_actions()`:

```python
def _execute_actions(self, actions, data_store):
    interactor = RunActionsOrchestrator(data_store=data_store)
    errors = interactor.run_all_checks(actions=actions)
    if errors:
        self._export_errors_to_csv(errors=errors)
        raise BadRequest("Run Actions Failed, Check in the csv errors")
    return interactor.execute_all(actions=actions)
```

---

## BPSTemplateRunActionRegistry

**File**: `bps/configio/bps_template/run_actions_handlers/registry.py`

Maps `(entity_type, action_type)` tuples to handler classes.

```python
class BPSTemplateRunActionRegistry:
    _registry: Dict[
        Tuple[GenerateEntityActionEnum, ConfigChangeActionEnum],
        Type[BaseConfigAction],
    ] = {}

    @classmethod
    def register(cls, entity_type, action_type):
        def decorator(action_class):
            cls._registry[(entity_type, action_type)] = action_class
            return action_class
        return decorator

    @classmethod
    def get_handler(cls, entity_type, action_type):
        return cls._registry.get((entity_type, action_type))

register_bps_template_run_action = BPSTemplateRunActionRegistry.register
```

### Usage

```python
from bps.configio.bps_template.run_actions_handlers.registry import (
    register_bps_template_run_action,
)

@register_bps_template_run_action(
    GenerateEntityActionEnum.TDR_ACCOUNT,
    ConfigChangeActionEnum.CREATE,
)
class TdrAccountCreateAction(BaseConfigAction):
    ...
```

---

## BaseConfigAction

**File**: `bps/configio/core/generate_actions_utils/base_action_handler.py`

Abstract base class for all action handlers.

```python
class BaseConfigAction(ABC):
    def __init__(self, data_store) -> None:
        self._data_store = data_store

    @property
    @abstractmethod
    def entity_type(self) -> GenerateEntityActionEnum:
        """The entity type this action handles."""

    @property
    @abstractmethod
    def action_type(self) -> ConfigChangeActionEnum:
        """The action type this handles (CREATE/UPDATE/DELETE)."""

    @abstractmethod
    def run_check(self, action: ChangeConfigActionDTO) -> List[RunActionErrorDTO]:
        """Validate the action. Return empty list if valid."""

    @abstractmethod
    def execute(self, action: ChangeConfigActionDTO) -> None:
        """Execute the action. Called only after all validations pass."""
```

---

## Handler Implementation Pattern

### Naming Convention

`{Entity}{ActionType}Action`

| Entity | Action | Class Name |
|--------|--------|-----------|
| TdrAccount | CREATE | `TdrAccountCreateAction` |
| TdrAccountTransaction | CREATE | `TdrAccountTransactionCreateAction` |
| TdrAccountTransactionLog | CREATE | `TdrAccountTransactionLogCreateAction` |
| PipelineItemRemarks | CREATE | `PipelineItemRemarksCreateAction` |
| PipelineItemRemarks | UPDATE | `PipelineItemRemarksUpdateAction` |

### Complete Handler Example

**File**: `bps/configio/tdr_bank/run_actions_handlers/tdr_account_create_action.py`

```python
from bps.configio.bps_template.constants.action_enums import (
    ConfigChangeActionEnum,
    GenerateEntityActionEnum,
)
from bps.configio.bps_template.dtos import (
    ChangeConfigActionDTO,
    RunActionErrorDTO,
)
from bps.configio.bps_template.run_actions_handlers.registry import (
    register_bps_template_run_action,
)
from bps.configio.core.generate_actions_utils.base_action_handler import (
    BaseConfigAction,
)


@register_bps_template_run_action(
    GenerateEntityActionEnum.TDR_ACCOUNT,
    ConfigChangeActionEnum.CREATE,
)
class TdrAccountCreateAction(BaseConfigAction):
    @property
    def entity_type(self) -> GenerateEntityActionEnum:
        return GenerateEntityActionEnum.TDR_ACCOUNT

    @property
    def action_type(self) -> ConfigChangeActionEnum:
        return ConfigChangeActionEnum.CREATE

    @property
    def tdr_adapter(self) -> TDRAdapter:
        return TDRAdapter()

    def run_check(self, action: ChangeConfigActionDTO) -> List[RunActionErrorDTO]:
        return self.tdr_adapter.run_checks_for_create_tdr_account(
            change_config_action_dto=action,
            data_store=self._data_store,
        )

    def execute(self, action: ChangeConfigActionDTO) -> None:
        self.tdr_adapter.create_tdr_account(change_config_action_dto=action)
```

**Note**: The `tdr_adapter` property is defined on the handler class itself, not on `BaseConfigAction`. Each handler defines its own adapter/service properties as needed.

### `run_check()` Guidelines

- Return `List[RunActionErrorDTO]` — empty list means valid
- Validate business rules (uniqueness, references exist, value constraints)
- Use error codes from `RunActionErrorCodeEnum`
- Never modify state during validation

### `execute()` Guidelines

- Called only after ALL actions pass `run_check()`
- Typically delegates to an adapter or service method
- Can modify the DataStore (e.g., register new IDs)
- Runs within the `@transaction.atomic()` from `ImportInteractor`

---

## RunActionErrorDTO

**File**: `bps/configio/bps_template/dtos.py`

```python
@dataclass
class RunActionErrorDTO:
    error_code: RunActionErrorCodeEnum
    message: str
    action: ChangeConfigActionDTO
```

---

## RunActionErrorCodeEnum

**File**: `bps/configio/bps_template/constants/action_enums.py`

Organized by entity type:

| Category | Examples |
|----------|---------|
| General | `NO_HANDLER_FOUND` |
| Template | `TEMPLATE_CREATE_DUPLICATE_NAME`, `TEMPLATE_UPDATE_IMMUTABLE_FIELD` |
| Section | `SECTION_NAME_ALREADY_EXISTS` |
| Field | `FIELD_CREATE_DUPLICATE_NAME`, `FIELD_UPDATE_TYPE_CHANGE_NOT_ALLOWED` |
| TDR Account | `ACCOUNT_NO_NOT_UNIQUE`, `HOLDER_USER_NOT_FOUND`, `INITIAL_BALANCE_NOT_POSITIVE` |
| Transaction | `TDR_ACCOUNT_NOT_FOUND`, `TRANSACTION_VALUE_NOT_POSITIVE` |
| Pipeline | `DUPLICATE_PIPELINE_NAME`, `INVALID_DEFAULT_STAGE_ID` |

When adding new entity types, add error codes to this enum.

---

## Error Export Pattern

When `run_all_checks()` returns errors, they are exported to `errors.csv`:

```python
@staticmethod
def _export_errors_to_csv(errors: List[RunActionErrorDTO]) -> None:
    csv_writer = CSVWriter()
    records = [
        {
            "error_code": error.error_code.value,
            "message": error.message,
            "entity_type": error.action.entity_type.value,
            "action_type": error.action.action.value,
            "entity_id": error.action.entity_id,
        }
        for error in errors
    ]
    csv_writer.write_csv(file_path="errors.csv", records=records)
```

---

## Registration Side-Effect Pattern

Like action generators, run action handlers must be imported to trigger decorator registration.

### `__init__.py` for Handlers

**File**: `bps/configio/tdr_bank/run_actions_handlers/__init__.py`

```python
from .tdr_account_create_action import TdrAccountCreateAction
from .tdr_account_transaction_create_action import TdrAccountTransactionCreateAction
from .tdr_account_transaction_log_create_action import TdrAccountTransactionLogCreateAction
from .pipeline_item_remarks_create_action import PipelineItemRemarksCreateAction
from .pipeline_item_remarks_update_action import PipelineItemRemarksUpdateAction
```

### ImportStore Must Import the Package

```python
# At the top of import_store.py
import bps.configio.tdr_bank.run_actions_handlers  # noqa: F401
```

---

## Cross-App Isolation Warning

run_actions_handlers live in `bps/configio/<module>/run_actions_handlers/`. They should not import from `sales_crm_core` internals. All cross-app calls go through the service adapter:

```python
@property
def sale_crm_service(self):
    from bps.adapters.service_adapter import get_service_adapter
    return get_service_adapter().sales_crm_service

def run_check(self, action: ChangeConfigActionDTO) -> List[RunActionErrorDTO]:
    errors = self.sale_crm_service.validate_create_<entity>_config(
        <entity>_config=action.entity_dto,
        data_store=self._data_store,
        account_id=self._data_store.account_id,
    )
    ...

def execute(self, action: ChangeConfigActionDTO) -> None:
    self.sale_crm_service.create_<entity>_config(
        <entity>_config=action.entity_dto,
        data_store=self._data_store,
        account_id=self._data_store.account_id,
    )
```

Violation pattern to never repeat:
```python
# NEVER DO THIS in bps/
from sales_crm_core.interactors.configio.relations.relation.relation_handler import RelationHandler
handler = RelationHandler(data_store=data_store)
handler.create(entity=action.entity_dto)
```

---

## Creating a New Handler Checklist

1. Choose the correct base class: `BaseConfigAction`
2. Register with `@register_bps_template_run_action(entity_type, action_type)`
3. Implement `entity_type` and `action_type` properties
4. Implement `run_check()` with appropriate error codes
5. Implement `execute()` with adapter/service calls
6. Add the handler import to `__init__.py`
7. Add any new error codes to `RunActionErrorCodeEnum`
