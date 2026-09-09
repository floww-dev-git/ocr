---
name: add-automation-workflow-node
description: Add a new automation workflow node type — covering node type registration, configuration DTOs, storage interface and implementation, GraphQL mutation, execution interactor, and exec-log DTO. Use when the user says "add a new node", "implement a new workflow node type", "create a node for automation workflows", or names a new node type to implement.
argument-hint: "[node type name and description of what it does]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Add Automation Workflow Node

Implement a new automation workflow node type: $ARGUMENTS

## Purpose of the process

Create a fully functional workflow node from scratch. A node is a step in an automation workflow tree. It has two halves: **configuration** (how the user sets it up in the UI, stored in the DB) and **execution** (what happens when a workflow runs and reaches this node).

This process is authoritative for both halves. Both must be completed in the same implementation — partial delivery (config without execution, or execution without config) is not acceptable.

**Authority boundaries:**
- You MAY create new files in `automation_workflows/` and `sales_crm_graphql/automation_workflows/` following the patterns below
- Add the new `NodeType` enum value to the existing `NodeType` enum — do not create a new enum
- Register the new node type in the `NODE_DTO` union type in `automation_workflows/interactors/nodes/__init__.py`
- Add a new branch to `_execute_node_based_on_type` in `execute_node_interactor.py`
- Add abstract methods to `NodeStorageInterface` AND implement them in `NodeStorageImpl` — do not leave an abstract method without an implementation
- Do not modify `ActionTypeEnum` — it is a legacy enum with only 6 values and is not what controls new node dispatch
- Do not add Django ORM logic inside interactors
- Write tests for the config interactor and the execution interactor

**Process invariants:**
- Every node that stores config beyond the `Node.exec_config` TextField follows the same pattern: one config method on `NodeStorageInterface` + one concrete implementation
- `NodeConfigStatus` must always be computed deterministically from the config DTO — never hardcoded
- Node trees use `parent_node_result` (TRUE/FALSE) for branching — all new action nodes return `NodeResultEnum.TRUE` implicitly (the dispatcher returns `None` as `node_result`, which downstream treats as TRUE)
- Execution always receives a PUBLISHED `exec_config` snapshot — the `exec_config` TextField on `Node` is the serialized config at publish time

---

## Input

Required before starting:
1. **Node type name** — the new `NodeType` enum value (SCREAMING_SNAKE_CASE, e.g. `SEND_EMAIL`)
2. **What the node does at execution time** — the business action performed on the pipeline item
3. **What configuration the node needs** — the fields a user fills in when building a workflow
4. **Which external service (if any) it calls** — which adapter it will use

Optional but clarify if ambiguous:
- Whether the node can return a failure result (most action nodes do NOT branch on failure — they add to `failed_node_ids` and continue)
- Whether the node modifies `pipeline_item_changed_fields` (needed for field-level tracking, e.g. stage updates)
- Whether the node's config uses a `FilterSet` (only needed for nodes that evaluate conditions on related records)

---

## Steps

### Step 1: Understand the request

1. Read `automation_workflows/constants/enum.py` to confirm the node type name does not already exist in `NodeType`
2. Read `automation_workflows/interactors/nodes/__init__.py` to see the current `NODE_DTO` union
3. Ask the user to confirm node type name, config fields, and runtime behavior before writing any code
4. Propose a concrete plan (file list + brief description of each) — get approval before proceeding

### Step 2: Register the node type

File: `automation_workflows/constants/enum.py`

**2a. Add the enum value:**
```python
YOUR_NODE_TYPE = "YOUR_NODE_TYPE"
```

**2b. Add to `action_node_types()` classmethod** (~line 87 in the same file):

The `action_node_types()` classmethod returns a list of all action node type values. After adding the enum value, ALSO add an entry to this list:
```python
@classmethod
def action_node_types(cls) -> List[str]:
    return [
        # ... existing entries ...
        cls.YOUR_NODE_TYPE.value,  # add this line
    ]
```

This classmethod is used by the validator to confirm the node is a valid action node. Omitting it causes `ValidateNodeCreationInteractor` to reject creation at runtime.

**2c. Add a `YourNodeTypeNodeResponseKeys` enum class** (at the bottom of the enum section, near similar `*NodeResponseKeys` classes):

```python
class YourNodeTypeNodeResponseKeys(BaseEnumClass, enum.Enum):
    # Define every key your execution interactor returns in its result dict
    SOME_RESULT_KEY = "some_result_key"
    ANOTHER_KEY = "another_key"
```

Use this enum as the source of truth for key strings when building the result dict in the execution interactor. Never use raw string literals as dict keys in the result.

**2d. Register in trigger-event compatibility maps** in `automation_workflows/constants/config.py`:

There are two main maps that control where the node is available:

1. **`SUPPORTED_EVENT_BASED_TRIGGERS_MAP`** (~line 355) — 2-level nesting: `{entity → {event_type → [node_types]}}`. Add to every `(entity, event_type)` combination where this node should be usable.

2. **`SUPPORTED_SCHEDULED_TRIGGERS_MAP`** (~line 592) — 1-level nesting: `{entity → [node_types]}`. Add to every entity where this node should be usable in scheduled workflows.

Steps:
1. Read `automation_workflows/constants/config.py` in full
2. For `SUPPORTED_EVENT_BASED_TRIGGERS_MAP`, decide which `(entity, event_type)` combos support this node — add `NodeType.YOUR_NODE_TYPE.value` to each applicable list
3. For `SUPPORTED_SCHEDULED_TRIGGERS_MAP`, decide which entities support this node — add to each applicable list
4. Also check for any OTHER maps in the file that reference node types (there may be additional maps for specific features)

Decision boundary: If the node is a generic action (e.g. send email, update field), add it to all entries in both maps. If it is trigger-specific (e.g. only makes sense on pipeline item events), add it only to those entries.

### Step 3: Define configuration DTOs

File: `automation_workflows/interactors/nodes/dtos.py`

Add three DTOs in the correct sections (marked by comments in that file):

**3a. Create DTO** (in the `# ------------------- Create Node DTOs ----------------` section):
```python
@dataclass
class CreateNodeYourNodeTypeDTO(BaseCreateNodeDTO):
    # All fields that the user configures. Use Optional only when the field
    # genuinely has no value at creation time (partial configuration allowed).
    your_config_field: SomeType
    another_field: Optional[str]
```

**3b. Update DTO** (in the `# -------------------- Update Node DTOs --------------------` section):
```python
@dataclass
class UpdateNodeYourNodeTypeDTO(BaseUpdateNodeDTO):
    # Mirror the create DTO fields, all Optional unless required on every update
    your_config_field: Optional[SomeType]
    another_field: Optional[str]
```

**3c. Response/Read DTO** (in the `# --------------------- Node Response DTOs ---------------------` section):
```python
@dataclass
class YourNodeTypeNodeDTO(BaseNodeDTO):
    # Fields returned when fetching node config. Mirror the stored config.
    your_config_field: Optional[SomeType]
    another_field: Optional[str]
```

Invariant: Never add `Optional` attributes unless the value is genuinely absent at runtime. Match field names exactly to the domain terminology.

### Step 4: Register in NODE_DTO union

File: `automation_workflows/interactors/nodes/__init__.py`

Add `dtos.YourNodeTypeNodeDTO` to the `NODE_DTO` Union type.

### Step 5: Add execution log DTO

File: `automation_workflows/interactors/execution/dtos.py`

Add in the execution log DTOs section:

```python
@dataclass
class YourNodeTypeNodeExecLogResultDTO:
    # The meaningful output of execution. What did the node produce/affect?
    # Examples: created IDs, counts, status codes, affected field IDs
    some_result_field: str

@dataclass
class YourNodeTypeNodeExecLogDTO(BaseNodeExecLogDTO):
    result: Optional[YourNodeTypeNodeExecLogResultDTO]
```

If the node produces no meaningful result (e.g. a fire-and-forget action), use `pass` body:
```python
@dataclass
class YourNodeTypeNodeExecLogDTO(BaseNodeExecLogDTO):
    pass
```

Also add `YourNodeTypeNodeExecLogDTO` to the `NODE_EXEC_LOG_DTOS_UNION` at the bottom of that file.

### Step 6: Add storage interface methods

File: `automation_workflows/interactors/storage_interfaces/node_storage_interface.py`

Add two abstract methods:
```python
@abc.abstractmethod
def create_node_your_node_type(
    self,
    node_dto: dtos.CreateNodeYourNodeTypeDTO,
    create_node_extra_info_dto: dtos.CreateNodeExtraInfoDTO,
) -> dtos.YourNodeTypeNodeDTO:
    pass

@abc.abstractmethod
def update_node_your_node_type(
    self,
    node_dto: dtos.UpdateNodeYourNodeTypeDTO,
    node_config_status: NodeConfigStatus,
) -> dtos.YourNodeTypeNodeDTO:
    pass
```

Decision boundary: If the node's config is entirely stored in `Node.exec_config` as JSON (no separate DB table), you still need these methods — the implementation serializes/deserializes that JSON.

### Step 7: Implement storage methods

File: `automation_workflows/storages/node_storage_impl.py`

Implement both abstract methods from Step 6. Follow the project pattern exactly:

**7a. Create method:**
```python
def create_node_your_node_type(
    self,
    node_dto: dtos.CreateNodeYourNodeTypeDTO,
    create_node_extra_info_dto: dtos.CreateNodeExtraInfoDTO,
) -> dtos.YourNodeTypeNodeDTO:
    exec_config = self._get_your_node_type_node_exec_config(node_dto=node_dto)

    node_obj = Node.objects.create(
        name=node_dto.name,
        automation_workflow_exec_config_id=create_node_extra_info_dto.automation_workflow_exec_config_id,
        node_type=node_dto.node_type,
        config_status=create_node_extra_info_dto.node_config_status,
        parent_node_id=node_dto.parent_node_id,
        parent_node_result=node_dto.parent_node_result,
        exec_config=exec_config,
        order=create_node_extra_info_dto.node_order,
    )

    return self._get_your_node_type_node_dto(node_obj=node_obj)
```

**7b. Update method:**
```python
def update_node_your_node_type(
    self,
    node_dto: dtos.UpdateNodeYourNodeTypeDTO,
    node_config_status: NodeConfigStatus,
) -> dtos.YourNodeTypeNodeDTO:
    exec_config = self._get_your_node_type_node_exec_config(node_dto=node_dto)

    node_obj = Node.objects.get(id=node_dto.node_id)
    node_obj.exec_config = exec_config
    node_obj.config_status = node_config_status
    node_obj.save()

    return self._get_your_node_type_node_dto(node_obj=node_obj)
```

**Serializer** (`_get_your_node_type_node_exec_config`) — converts DTO to JSON string for `Node.exec_config`:
```python
@staticmethod
def _get_your_node_type_node_exec_config(
    node_dto: Union[dtos.CreateNodeYourNodeTypeDTO, dtos.UpdateNodeYourNodeTypeDTO, dtos.YourNodeTypeNodeDTO],
) -> str:
    return json.dumps({
        "your_config_field": node_dto.your_config_field,
        "another_field": node_dto.another_field,
    })
```

**Deserializer** (`_get_your_node_type_node_dto`) — converts Node model to DTO:
```python
def _get_your_node_type_node_dto(self, node_obj: Node) -> dtos.YourNodeTypeNodeDTO:
    base_node_dto = self._get_base_node_dto(node_obj=node_obj)
    exec_config = json.loads(node_obj.exec_config)
    return dtos.YourNodeTypeNodeDTO(
        **base_node_dto.__dict__,
        your_config_field=exec_config["your_config_field"],
        another_field=exec_config.get("another_field"),
    )
```

Invariant: Use `_get_*_node_dto()` deserializer for all model-to-DTO conversions and `_get_*_node_exec_config()` serializer for DTO-to-JSON. Never return a raw ORM model. Use `_get_base_node_dto(node_obj)` to get base fields and spread via `**base_node_dto.__dict__`.

**7c. Register in the DTO getter map** (~line 177 in `node_storage_impl.py`):

There is a dict that maps `NodeType.*.value` strings to `self._get_*_node_dto` methods. Add an entry for the new node:
```python
NodeType.YOUR_NODE_TYPE.value: self._get_your_node_type_node_dto,
```

This map is used when fetching node config by node ID. Omitting it causes a `KeyError` at runtime when the UI loads the node.

**7d. Register in the exec config getter map** (~line 210 in `node_storage_impl.py`):

There is a second dict that maps `NodeType.*.value` strings to `self._get_*_node_exec_config` methods. Add an entry:
```python
NodeType.YOUR_NODE_TYPE.value: self._get_your_node_type_node_exec_config,
```

This map is used when building the published exec config snapshot. Omitting it causes a `KeyError` at publish time.

### Step 8: Write the configuration interactor

File: `automation_workflows/interactors/nodes/your_node_type_node.py`

```python
from automation_workflows.constants.enum import NodeConfigStatus, NodeType
from automation_workflows.exceptions.node_exceptions import NotYourNodeTypeNodeType
from automation_workflows.interactors.nodes import NodeResultDTO
from automation_workflows.interactors.nodes.base_node import BaseNodeInteractor
from automation_workflows.interactors.nodes.dtos import (
    CreateNodeExtraInfoDTO,
    CreateNodeYourNodeTypeDTO,
    UpdateNodeYourNodeTypeDTO,
)


class YourNodeTypeNodeInteractor(BaseNodeInteractor):
    def create_node(
        self, user_id: str, node_dto: CreateNodeYourNodeTypeDTO
    ) -> NodeResultDTO:
        aw_pipeline_id = self._validate_creation(user_id=user_id, node_dto=node_dto)
        workflow_exec_config_id = self.automation_workflow_storage.get_editable_automation_workflow_exec_config_id(
            automation_workflow_id=node_dto.automation_workflow_id
        )
        # Run any node-specific validation here
        self._validate_node_config(node_dto=node_dto)

        extra_info_dto = self._get_create_node_extra_info_dto(
            node_dto=node_dto, workflow_exec_config_id=workflow_exec_config_id
        )
        self.update_parent_node_result(base_create_dto=node_dto)

        created_node_dto = self.node_storage.create_node_your_node_type(
            node_dto=node_dto, create_node_extra_info_dto=extra_info_dto
        )
        self.update_child_parent_node(
            child_node_id=node_dto.child_node_id,
            child_parent_node_id=created_node_dto.node_id,
            child_parent_node_result=node_dto.child_parent_node_result,
        )
        return NodeResultDTO(
            automation_workflow_id=node_dto.automation_workflow_id,
            node_dto=created_node_dto,
        )

    def update_node(
        self, user_id: str, update_node_dto: UpdateNodeYourNodeTypeDTO
    ) -> NodeResultDTO:
        node_dto = super().validate_updation(
            user_id=user_id, update_node_dto=update_node_dto
        )
        if node_dto.node_type != NodeType.YOUR_NODE_TYPE.value:
            raise NotYourNodeTypeNodeType(node_id=node_dto.node_id)

        self._validate_node_config(node_dto=update_node_dto)
        config_status = self._get_node_config_status(update_node_dto)
        automation_workflow_id = self.automation_workflow_storage.get_workflow_exec_config_workflow_id(
            workflow_exec_config_id=node_dto.automation_workflow_exec_config_id
        )
        updated_node_dto = self.node_storage.update_node_your_node_type(
            node_dto=update_node_dto, node_config_status=config_status
        )
        return NodeResultDTO(
            automation_workflow_id=automation_workflow_id,
            node_dto=updated_node_dto,
        )

    def _validate_creation(
        self, user_id: str, node_dto: CreateNodeYourNodeTypeDTO
    ) -> str:
        from automation_workflows.interactors.nodes.validators.validate_node_creation import (
            ValidateNodeCreationInteractor,
        )
        interactor = ValidateNodeCreationInteractor(
            node_storage=self.node_storage,
            trigger_storage=self.trigger_storage,
            automation_workflow_storage=self.automation_workflow_storage,
        )
        return interactor.validate_node_creation(
            user_id=user_id, create_node_dto=node_dto
        )

    @staticmethod
    def _validate_node_config(node_dto) -> None:
        # Raise domain exceptions for invalid config
        # Examples: missing required field IDs, invalid enum values
        pass

    @staticmethod
    def _get_node_config_status(node_dto) -> NodeConfigStatus:
        # Return CONFIGURED only when all required fields are present
        # Return PARTIALLY_CONFIGURED when optional fields are missing
        # noinspection PyTypeChecker
        is_fully_configured = bool(node_dto.your_required_field)
        if is_fully_configured:
            return NodeConfigStatus.CONFIGURED.value
        return NodeConfigStatus.PARTIALLY_CONFIGURED.value

    def _get_create_node_extra_info_dto(
        self,
        node_dto: CreateNodeYourNodeTypeDTO,
        workflow_exec_config_id: str,
    ) -> CreateNodeExtraInfoDTO:
        node_order = self.get_new_node_order(
            parent_node_id=node_dto.parent_node_id,
            automation_workflow_exec_config_id=workflow_exec_config_id,
            child_node_id=node_dto.child_node_id,
        )
        config_status = self._get_node_config_status(node_dto)
        return CreateNodeExtraInfoDTO(
            automation_workflow_exec_config_id=workflow_exec_config_id,
            node_config_status=config_status,
            node_order=node_order,
            filter_set_id=None,
        )
```

Invariant: `_validate_creation` always calls `ValidateNodeCreationInteractor`. Do not bypass it.

### Step 9: Write the execution interactor

Decision boundary: Use a dedicated file under `automation_workflows/interactors/execution/action_node/` when:
- The execution logic exceeds ~40 lines, OR
- The execution requires multiple service calls, OR
- The logic benefits from unit-testable isolation

Otherwise inline a private method on `ExecuteNodeInteractor`.

**For a dedicated executor class:**

File: `automation_workflows/interactors/execution/action_node/execute_your_node_type.py`

```python
from typing import Dict, Optional

from automation_workflows.adapters.your_service import YourService
from automation_workflows.interactors.nodes import dtos as node_dtos


class ExecuteYourNodeTypeInteractor:
    @property
    def your_service(self) -> YourService:
        from automation_workflows.adapters.service_adapter import get_service_adapter
        return get_service_adapter().your_service

    def execute_your_node_type(
        self,
        pipeline_item_id: str,
        node_dto: node_dtos.YourNodeTypeNodeDTO,
        # Add only the field-response maps this node actually needs
        latest_lead_fields: Dict[str, Optional[str]],
    ) -> Dict:
        # 1. Resolve values from lead fields using node config
        # 2. Call the external service
        # 3. Return a dict with response keys (use the ResponseKeys enum)
        result = self.your_service.do_something(
            pipeline_item_id=pipeline_item_id,
            config_value=node_dto.your_config_field,
        )
        return {
            YourNodeTypeNodeResponseKeys.SOME_RESULT_KEY.value: result.some_value,
        }
```

**If the node can partially fail** (e.g. main action succeeds but a secondary write fails), return a `Tuple[Dict, NodeExecLogStatusEnum]`:
```python
    def execute_your_node_type(self, ...) -> Tuple[Dict, NodeExecLogStatusEnum]:
        # ... main action ...
        node_status = NodeExecLogStatusEnum.DONE.value
        try:
            # secondary action that may fail independently
            self.your_service.secondary_action(...)
        except SomeExpectedException:
            node_status = NodeExecLogStatusEnum.FAILED.value
        return {
            YourNodeTypeNodeResponseKeys.SOME_RESULT_KEY.value: result.some_value,
        }, node_status
```

This 2-tuple pattern is used by `GENERATE_DOCUMENT`, `SIGN_DOCUMENT`, and other nodes where the main action succeeds but a secondary action (like copying a URL to a field) can fail independently. The dispatcher unpacks both values.

Rules for execution interactors:
- Accept only the field-response maps the node actually reads — do not accept all maps and ignore most of them
- Return a plain `Dict` (or `Tuple[Dict, NodeExecLogStatusEnum]` for partial failure) — the dispatcher stores the dict as `node_exec_result`
- Use `YourNodeTypeNodeResponseKeys` enum values as dict keys — never raw string literals
- Raise domain exceptions from `automation_workflows/exceptions/execution_exceptions.py` for unrecoverable failures
- Never catch bare `Exception` — let unhandled failures propagate to `ExecuteNodeInteractor.execute_node()` which wraps in `failed_node_ids`
- **Safe `field_type_map` access:** Never access `field_type_map[field_id]` directly — it will `KeyError` on fixed payload keys like `TO_STAGE`, `FROM_STAGE`, `TASK_COMPLETED_AT`. Always use `field_type_map.get(field_id)` first, validate the result is not `None`, then proceed:
  ```python
  field_type = field_type_map.get(field_id)
  if field_type is None:
      # handle missing field type (skip, use default, etc.)
      continue
  ```
- **`FROM_STAGE` / `TO_STAGE` handling:** If the node maps fields and the trigger is `STAGE_UPDATED`, the trigger payload includes `FROM_STAGE` and `TO_STAGE` as virtual payload keys (not real field IDs). These are defined in `TriggerPayloadKey` enum. When resolving field values, check if `value_from == FieldSourceType.TRIGGER_ENTITY_DETAILS.value` and handle these keys via the `trigger_entity_details` map, not the `latest_lead_fields` map.

### Step 10: Wire the executor into the dispatch

File: `automation_workflows/interactors/execution/execute_node_interactor.py`

**10a-i. Add one `elif` branch** inside `_execute_node_based_on_type`:

```python
elif node_type == NodeType.YOUR_NODE_TYPE.value:
    node_exec_result = self.execute_your_node_type_node(
        pipeline_item_id=exec_req_dto.lead_id,
        node_dto=node_dto,
        latest_lead_fields=config_data_map_dto.latest_lead_fields_maps_dto.formatted_response_map,
    )
```

If the executor returns a 2-tuple (partial failure pattern), unpack it:
```python
elif node_type == NodeType.YOUR_NODE_TYPE.value:
    (
        node_exec_result,
        node_status,
    ) = self.execute_your_node_type_node(
        pipeline_item_id=exec_req_dto.lead_id,
        node_dto=node_dto,
        latest_lead_fields=config_data_map_dto.latest_lead_fields_maps_dto.formatted_response_map,
    )
```

**10a-ii. Add a static wrapper method** at the bottom of `ExecuteNodeInteractor` (where the other `@staticmethod` wrappers like `execute_call_webhook_node`, `execute_generate_document_node` are):

```python
@staticmethod
def execute_your_node_type_node(
    pipeline_item_id: str,
    node_dto: node_dtos.YourNodeTypeNodeDTO,
    latest_lead_fields: Dict[str, Optional[str]],
) -> Dict:
    from automation_workflows.interactors.execution.action_node.execute_your_node_type import (
        ExecuteYourNodeTypeInteractor,
    )
    interactor = ExecuteYourNodeTypeInteractor()
    return interactor.execute_your_node_type(
        pipeline_item_id=pipeline_item_id,
        node_dto=node_dto,
        latest_lead_fields=latest_lead_fields,
    )
```

This pattern keeps the deferred import inside the static method and keeps the `elif` branch clean. All existing nodes use this pattern.

Decision boundary for which response map to pass:
- `internal_response_map` — when the node reads assignee/user field values (UUID strings)
- `third_party_response_map` — when the node sends data to external APIs (formatted strings)
- `formatted_response_map` — when the node uses human-readable text values
- `obj_response_map` — when the node reads full field response objects (e.g. file uploaders, complex types)
- `document_formatted_response_map` — for document generation nodes only

If the node modifies pipeline item fields (e.g. writes back a value), also extend `changed_pipeline_item_fields`:
```python
changed_pipeline_item_fields.extend([
    GofResponseFieldIdDTO(gof_response_id=None, field_id=field_id)
    for field_id in changed_field_ids
])
```

### Step 10b: Register in exec log transformation

File: `automation_workflows/interactors/execution/node_exec_logs_interactor.py`

There are two things to add here:

**10b-i. Add an entry to the converter map** (~line 138):
```python
NodeType.YOUR_NODE_TYPE.value: self._transform_your_node_type_node_log_dto,
```

**10b-ii. Add the `_transform_your_node_type_node_log_dto()` method**:
```python
def _transform_your_node_type_node_log_dto(
    self,
    node_log_dto: NodeExecutionLogDTO,
    failure_reason: Optional[str],
) -> execution_dtos.YourNodeTypeNodeExecLogDTO:
    base_node_dto = self._get_base_node_dto(
        node_type=NodeType.YOUR_NODE_TYPE.value,
        node_log_dto=node_log_dto,
        failure_reason=failure_reason,
    )
    result_dict = node_log_dto.result
    if not result_dict:
        return execution_dtos.YourNodeTypeNodeExecLogDTO(
            **base_node_dto.__dict__, result=None
        )
    result = execution_dtos.YourNodeTypeNodeExecLogResultDTO(
        some_result_field=result_dict[
            YourNodeTypeNodeResponseKeys.SOME_RESULT_KEY.value
        ],
    )
    return execution_dtos.YourNodeTypeNodeExecLogDTO(
        **base_node_dto.__dict__, result=result
    )
```

Key patterns:
- Method signature takes `(node_log_dto: NodeExecutionLogDTO, failure_reason: Optional[str])` — these are passed by the converter dispatch
- Use `self._get_base_node_dto(...)` to build base fields (node_exec_log_id, node_id, node_type, status, failure_reason)
- Spread base fields via `**base_node_dto.__dict__` — never manually set base fields
- Extract result from `node_log_dto.result` (a raw Dict) using `YourNodeTypeNodeResponseKeys` enum values

Omitting this step causes a `KeyError` at runtime whenever the exec log endpoint is called for a workflow that ran a node of this type.

### Step 10c: Register in field ID resolution interactors

**File A:** `automation_workflows/interactors/configuration/automation_workflows/get_field_ids_in_nodes_config.py`

There are two things to add:

**10c-i. Add an entry to the converter map** (~line 60):
```python
NodeType.YOUR_NODE_TYPE.value: self._get_your_node_type_node_field_ids,
```

**10c-ii. Add the method**:
```python
def _get_your_node_type_node_field_ids(
    self,
    node_dto: dtos.YourNodeTypeNodeDTO,
    entity_filters_dto: Optional[AutomationWorkflowEntityFiltersDTO],
) -> List[str]:
    # Return ALL field IDs referenced in this node's config.
    # If the node uses no field IDs, return [].
    return []
```

**Collect both left-side and right-side fields.** If the node has field mappings (field A = value from field B), you must collect both:
- **Left side (target):** the field being written TO — `field_mapping_dto.field_id`
- **Right side (source):** the field being read FROM — `field_mapping_dto.value` (when `value_from` is not `DIRECT_VALUE`)

Example from UPDATE_LEAD:
```python
for field_mapping_dto in node_dto.field_mapping_dtos:
    field_ids.append(field_mapping_dto.field_id)           # LEFT SIDE
    if field_mapping_dto.value_from in FieldSourceType.get_value_non_field_ids_source_types():
        continue
    field_ids.append(field_mapping_dto.value)               # RIGHT SIDE
```

Omitting left-side fields means the UI won't know which fields the node modifies. Omitting right-side fields means values won't be pre-fetched at execution time.

**File B:** `automation_workflows/interactors/configuration/automation_workflows/get_latest_lead_field_ids.py`

Same pattern as File A, but for lead field IDs:

**10c-iii. Add an entry to the converter map** (~line 61):
```python
NodeType.YOUR_NODE_TYPE.value: self._get_your_node_type_node_latest_lead_field_ids,
```

**10c-iv. Add the method**:
```python
def _get_your_node_type_node_latest_lead_field_ids(
    self, node_dto: dtos.YourNodeTypeNodeDTO
) -> List[str]:
    # Return the field IDs whose values must be fetched before execution.
    # These are included in the LatestLeadFieldResponseMapsDTO passed at runtime.
    return []
```

Omitting these steps means field values will not be pre-fetched for the node, causing `None` values at execution time for any field-mapped config.

### Step 11: Write the GraphQL mutation

**11a. Node response type**

File: `sales_crm_graphql/automation_workflows/nodes/types/types.py`

Add a GraphQL type that implements the `BaseNode` interface. The `BaseNode` interface provides the common fields (`node_id`, `name`, `node_type`, `config_status`, `order`, `parent_node_id`, `parent_node_result`, `automation_workflow_exec_config_id`). Only add node-specific fields:

```python
class YourNodeType(graphene.ObjectType):
    class Meta:
        interfaces = (BaseNode,)

    # Only your node-specific fields — BaseNode provides the common ones
    your_config_field = graphene.String()
    another_field = graphene.String()
```

**Also register in the `get_node_types()` function** (~line 937 in the same file):

There is a `get_node_types()` function that returns a list of all node GraphQL ObjectTypes. Add `YourNodeType` to this list:
```python
def get_node_types():
    return [
        # ... existing types ...
        YourNodeType,
    ]
```

The `Node` union and `NodeResult` union both use this function. Omitting this step means the union resolver cannot resolve nodes of this type and returns `null`.

**11b. NodeTypesConverter**

File: `sales_crm_graphql/automation_workflows/nodes/resolvers/node_types_converter.py`

Add a branch in the converter to map `YourNodeTypeNodeDTO` → `YourNodeType`.

**11c. GraphQL error type**

File: `sales_crm_graphql/automation_workflows/nodes/types/error_types.py`

Add a type-guard error type that implements the `GraphQLBaseError` interface:
```python
class NotYourNodeTypeNodeType(graphene.ObjectType):
    class Meta:
        interfaces = (GraphQLBaseError,)

    node_id = graphene.String(required=True)
```

This error type is returned when `update_node` is called on a node that is not of `YOUR_NODE_TYPE`. It must be listed in the `UpdateNodeYourNodeTypeResponse` union in the update mutation.

**11d. Create mutation**

File: `sales_crm_graphql/automation_workflows/nodes/mutations/create_nodes/your_node_type.py`

Follow the pattern from `generate_number_node.py` exactly:
- `class CreateNodeYourNodeTypeParams(BaseCreateNodeParams):` — add your config fields
- `class CreateNodeYourNodeTypeResponse(graphene.Union):` — list all standard error types
- `class CreateNodeYourNodeType(graphene.Mutation):` — wire to `YourNodeTypeNodeInteractor`
- Use `.value` when passing enum params to the DTO: `node_type=NodeType.YOUR_NODE_TYPE.value`
- Always use `.value` when passing any enum-typed param to a DTO attribute

**11e. Update mutation**

File: `sales_crm_graphql/automation_workflows/nodes/mutations/update_nodes/your_node_type.py`

Mirror the create mutation pattern but use `UpdateNodeYourNodeTypeDTO`. Include `NotYourNodeTypeNodeType` in the `UpdateNodeYourNodeTypeResponse` union.

**11f. GraphQL execution log types**

File: `sales_crm_graphql/automation_workflows/automation_workflows/types/types.py`

Add three things:

**11f-i.** A result type for the exec log:
```python
class YourNodeTypeNodeExecLogResult(graphene.ObjectType):
    some_result_field = graphene.String()
    another_key = graphene.String()
```

**11f-ii.** An exec log type that implements the `BaseNodeExecLog` interface (which provides `node_exec_log_id`, `node_id`, `status`, `failure_reason`):
```python
class YourNodeTypeNodeExecLog(graphene.ObjectType):
    class Meta:
        interfaces = (BaseNodeExecLog,)

    result = graphene.Field(YourNodeTypeNodeExecLogResult)
```

**11f-iii.** Register in `NODE_EXEC_LOG_GQL_TYPES` list (not a Union — it's a Python list used by the `NodeExecLog` Union class):
```python
NODE_EXEC_LOG_GQL_TYPES = [
    # ... existing types ...
    YourNodeTypeNodeExecLog,
]

class NodeExecLog(graphene.Union):
    class Meta:
        types = NODE_EXEC_LOG_GQL_TYPES
```

**11g. GraphQL execution log transformer**

File: `sales_crm_graphql/automation_workflows/automation_workflows/utils.py`

Add two things:

**11g-i.** Entry in the converter map (~line 78):
```python
NodeType.YOUR_NODE_TYPE.value: self._transform_your_node_type_node_log_dto,
```

**11g-ii.** The transformer method:
```python
def _transform_your_node_type_node_log_dto(
    self, node_exec_log_dto: exec_dtos.YourNodeTypeNodeExecLogDTO
) -> types.YourNodeTypeNodeExecLog:
    result_dto = node_exec_log_dto.result
    result_gql_type = None
    if result_dto:
        result_gql_type = types.YourNodeTypeNodeExecLogResult(
            some_result_field=result_dto.some_result_field,
        )
    return types.YourNodeTypeNodeExecLog(
        node_exec_log_id=node_exec_log_dto.node_exec_log_id,
        node_id=node_exec_log_dto.node_id,
        status=node_exec_log_dto.status,
        failure_reason=node_exec_log_dto.failure_reason,
        result=result_gql_type,
    )
```

Key patterns:
- Method signature takes `(node_exec_log_dto: exec_dtos.YourNodeTypeNodeExecLogDTO)` — the DTO comes from Step 10b
- Base fields passed to the GQL type are: `node_exec_log_id`, `node_id`, `status`, `failure_reason` — these match the `BaseNodeExecLog` interface
- Result DTO is extracted and converted to the GQL result type separately

Omitting 11f and 11g causes the exec log GraphQL query to return `null` for nodes of this type.

**11h. Register in schema**

File: `sales_crm_graphql/automation_workflows/nodes/mutations/__init__.py` (or wherever the node mutations are collected)

Add both `CreateNodeYourNodeType` and `UpdateNodeYourNodeType` to the mutation registry.

### Step 12: Add domain exceptions

File: `automation_workflows/exceptions/node_exceptions.py`

Add a type-guard exception for update_node validation:
```python
class NotYourNodeTypeNodeType(BaseExceptionClass):
    def __init__(self, node_id: str):
        super().__init__()
        self.node_id = node_id
```

Add any node-specific validation exceptions:
```python
class InvalidYourConfigField(BaseExceptionClass):
    def __init__(self, field_value: str):
        super().__init__()
        self.field_value = field_value
```

### Step 12b: Register error messages in `PrepareNodeErrorResponseInteractor`

File: `automation_workflows/interactors/execution/prepare_node_err_msg.py`

This interactor converts domain exceptions to user-facing error messages shown in execution logs. It uses a chain of `isinstance()` checks (NOT a dict map). For each new node-specific exception that can occur at **execution time**, add an `elif isinstance(err, YourException)` block before the final fallback at the end of the method:

```python
elif isinstance(err, YourNodeSpecificException):
    return "User-facing error message describing what went wrong"
```

If the exception carries context attributes (e.g. `field_id`, `entity_id`), format them into the message:
```python
elif isinstance(err, YourNodeSpecificException):
    return f"Could not process field {err.field_id}: {err.reason}"
```

Rules:
- Only register exceptions that can be raised during **execution** (not configuration-time validation)
- Place new blocks BEFORE the final `else` fallback (which returns a generic message)
- Order matters for specificity — more specific exception types should come before more general parent types
- Omitting this step means execution failures for this node show a generic error message in the UI instead of a helpful one

### Step 13: Write tests

**Model factory:**

File: `automation_workflows/tests/factories/models.py`

Add a factory for creating `Node` model instances with the new node type:
```python
class YourNodeTypeNodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Node

    node_type = NodeType.YOUR_NODE_TYPE.value
    config_status = NodeConfigStatus.CONFIGURED.value
    # Set your node's default exec_config JSON here
    exec_config = factory.LazyFunction(lambda: json.dumps({
        "your_config_field": "default_value",
    }))
    automation_workflow_exec_config = factory.SubFactory(AutomationWorkFlowExecConfigFactory)
```

**DTO factories:**

File: `automation_workflows/tests/factories/interactor_dtos/node_dtos.py`

Add three factories — create DTO, update DTO, and response DTO:
```python
class CreateNodeYourNodeTypeDTOFactory(factory.Factory):
    class Meta:
        model = CreateNodeYourNodeTypeDTO

    node_type = NodeType.YOUR_NODE_TYPE.value
    your_config_field = "default_value"
    # ... other fields with sensible defaults

class UpdateNodeYourNodeTypeDTOFactory(factory.Factory):
    class Meta:
        model = UpdateNodeYourNodeTypeDTO

    node_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    your_config_field = "updated_value"

class YourNodeTypeNodeDTOFactory(factory.Factory):
    class Meta:
        model = YourNodeTypeNodeDTO

    node_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    node_type = NodeType.YOUR_NODE_TYPE.value
    your_config_field = "value"
```

**Config interactor test:**

File: `automation_workflows/tests/interactors/nodes/test_your_node_type_node.py`

Required test scenarios:
- `test_create_node_success` — valid DTO, assert storage called and NodeResultDTO returned
- `test_create_node_with_invalid_config_raises_exception` — invalid config field raises domain exception
- `test_update_node_success` — valid update, assert storage update called
- `test_update_node_wrong_node_type_raises_exception` — non-matching node_type raises `NotYourNodeTypeNodeType`
- `test_get_node_config_status_configured` — full config returns `CONFIGURED`
- `test_get_node_config_status_partially_configured` — missing required field returns `PARTIALLY_CONFIGURED`

**Execution interactor test:**

File: `automation_workflows/tests/interactors/execution/test_execute_your_node_type.py`

Required test scenarios:
- `test_execute_success` — happy path, assert service called with correct params and correct dict returned
- `test_execute_handles_service_failure` — service raises exception, assert it propagates (no swallowing)
- Any output-specific assertions (e.g. correct field IDs collected in changed_fields)

Run tests with:
```bash
source venv/bin/activate && pytest automation_workflows/tests/interactors/nodes/test_your_node_type_node.py -v --no-migrations
pytest automation_workflows/tests/interactors/execution/test_execute_your_node_type.py -v --no-migrations
```

All tests must pass before proceeding to self-review.

### Step 14: Self-review checklist

Run through each item before declaring done:

**Registration:**
- [ ] `NodeType.YOUR_NODE_TYPE` added to enum in `constants/enum.py`
- [ ] `NodeType.YOUR_NODE_TYPE.value` added to `action_node_types()` classmethod
- [ ] `YourNodeTypeNodeResponseKeys` enum class added in `constants/enum.py`
- [ ] New node type added to ALL applicable maps in `constants/config.py` (read the full file, check every dict)

**DTOs:**
- [ ] `CreateNodeYourNodeTypeDTO`, `UpdateNodeYourNodeTypeDTO`, `YourNodeTypeNodeDTO` in `interactors/nodes/dtos.py`
- [ ] `YourNodeTypeNodeDTO` in `NODE_DTO` union in `interactors/nodes/__init__.py`
- [ ] `YourNodeTypeNodeExecLogDTO` in `interactors/execution/dtos.py` and in `NODE_EXEC_LOG_DTOS_UNION`

**Storage layer:**
- [ ] Abstract methods added to `NodeStorageInterface`
- [ ] Both abstract methods implemented in `NodeStorageImpl`
- [ ] `_get_your_node_type_node_dto()` deserializer and `_get_your_node_type_node_exec_config()` serializer implemented
- [ ] Entry added to DTO getter map (~line 177 in `node_storage_impl.py`)
- [ ] Entry added to exec config getter map (~line 210 in `node_storage_impl.py`)

**Configuration interactor:**
- [ ] `YourNodeTypeNodeInteractor` file created and `create_node` + `update_node` implemented
- [ ] `_validate_creation` calls `ValidateNodeCreationInteractor`
- [ ] Domain exceptions added in `exceptions/node_exceptions.py`

**Execution interactor:**
- [ ] `ExecuteYourNodeTypeInteractor` (or inline method) created
- [ ] `elif` branch added in `_execute_node_based_on_type`
- [ ] `@staticmethod` wrapper method added at bottom of `ExecuteNodeInteractor`
- [ ] Entry added in `node_exec_logs_interactor.py` converter map
- [ ] `_transform_your_node_type_node_log_dto()` method added in `node_exec_logs_interactor.py`
- [ ] Entry added in `get_field_ids_in_nodes_config.py` converter map + method (collects BOTH left-side and right-side fields)
- [ ] Entry added in `get_latest_lead_field_ids.py` converter map + method
- [ ] Node-specific execution exceptions registered in `prepare_node_err_msg.py` (isinstance checks)
- [ ] `field_type_map` accessed safely with `.get()`, not `[]`

**GraphQL layer:**
- [ ] `YourNodeType(graphene.ObjectType)` added in `nodes/types/types.py`
- [ ] `YourNodeType` added to `Node` union in `nodes/types/types.py`
- [ ] `NotYourNodeTypeNodeType` error type added in `nodes/types/error_types.py`
- [ ] `NodeTypesConverter` handles `YourNodeTypeNodeDTO` → `YourNodeType`
- [ ] Create and update mutations written and registered in schema
- [ ] `YourNodeTypeNodeExecLogResult` and `YourNodeTypeNodeExecLog` types added in `automation_workflows/types/types.py`
- [ ] `YourNodeTypeNodeExecLog` added to `NODE_EXEC_LOG_GQL_TYPES` union
- [ ] Transformer entry and method added in `automation_workflows/utils.py`

**Tests:**
- [ ] Model factory `YourNodeTypeNodeFactory` added in `tests/factories/models.py`
- [ ] DTO factories added in `tests/factories/interactor_dtos/node_dtos.py` (create, update, response)
- [ ] Config interactor tests written and passing
- [ ] Execution interactor tests written and passing

**Code quality:**
- [ ] No bare `except Exception` used
- [ ] All enum values passed as `.value` in DTOs
- [ ] `# noinspection PyTypeChecker` added where enum `.value` is assigned to enum-typed attribute
- [ ] No storage calls inside loops
- [ ] No `print` or `logger` statements in business logic
- [ ] All methods have type hints

---

## Output

When complete, the following will exist and be functional:

1. New `NodeType` enum value registered, added to `action_node_types()`, and added to `SUPPORTED_EVENT_BASED_TRIGGERS_MAP` + `SUPPORTED_SCHEDULED_TRIGGERS_MAP` in `constants/config.py`
2. `YourNodeTypeNodeResponseKeys` enum class in `constants/enum.py`
3. Three config DTOs (create, update, read) in `interactors/nodes/dtos.py`
4. `YourNodeTypeNodeDTO` registered in `NODE_DTO` union
5. Execution log DTOs in `interactors/execution/dtos.py` and registered in `NODE_EXEC_LOG_DTOS_UNION`
6. Storage interface abstract methods + concrete implementation in `storages/node_storage_impl.py`, with entries in both getter maps
7. Config interactor class `YourNodeTypeNodeInteractor` in `interactors/nodes/`
8. Execution interactor `ExecuteYourNodeTypeInteractor` in `interactors/execution/action_node/`
9. Dispatch branch + `@staticmethod` wrapper in `ExecuteNodeInteractor`
10. Exec log transform entry + method in `node_exec_logs_interactor.py`
11. Field ID resolution entries + methods in `get_field_ids_in_nodes_config.py` (left+right side) and `get_latest_lead_field_ids.py`
12. Error messages registered in `prepare_node_err_msg.py` for execution-time exceptions
13. GraphQL node type in `nodes/types/types.py` (with `BaseNode` interface), registered in `Node` union
14. GraphQL error type `NotYourNodeTypeNodeType` in `nodes/types/error_types.py` (with `GraphQLBaseError` interface)
15. GraphQL create and update mutations in `sales_crm_graphql/automation_workflows/nodes/mutations/`
16. GraphQL exec log types in `automation_workflows/types/types.py` (with `BaseNodeExecLog` interface), registered in `NODE_EXEC_LOG_GQL_TYPES`
17. GraphQL exec log transformer entry + method in `automation_workflows/utils.py`
18. Domain exceptions in `exceptions/node_exceptions.py`
19. Model factory in `tests/factories/models.py`
20. DTO factories (create, update, response) in `tests/factories/interactor_dtos/node_dtos.py`
21. Unit tests for config and execution interactors, all passing

---

## Special Cases and respective Handling

### Node needs a FilterSet (e.g. for evaluating conditions on related records)

Detection: The node type uses condition filters to determine which records to act on (like `UPDATE_RELATED_RECORDS`).

Handling:
- Add `NodeType.YOUR_NODE_TYPE.value` to the `node_types_having_filters()` classmethod in `automation_workflows/constants/enum.py` (~line 82)
- Set `filter_set_id` in `CreateNodeExtraInfoDTO` rather than `None`
- Add filter set creation/deletion logic to the storage implementation
- Pass `entity_filters_map` from `config_data_map_dto` to the execution interactor

Validation: Confirm that a `FilterSet` FK exists on `Node` model — it does (with `SET_NULL`, optional). Currently only CONDITION and UPDATE_RELATED_RECORDS use this.

### Node modifies pipeline item fields

Detection: The node writes a value back to the pipeline item's field responses (e.g. stage updates, assignee changes, field value writes).

Handling:
- The execution method must return both the `node_exec_result` dict AND a `List[str]` of changed `field_id` values
- In `_execute_node_based_on_type`, unpack the tuple and extend `changed_pipeline_item_fields`:
  ```python
  node_exec_result, changed_field_ids = executor.execute_...()
  changed_pipeline_item_fields.extend([
      GofResponseFieldIdDTO(gof_response_id=None, field_id=fid)
      for fid in changed_field_ids
  ])
  ```

Validation: Confirm `GofResponseFieldIdDTO` is imported at the top of `execute_node_interactor.py`.

### Node calls an external HTTP service (webhook-style)

Detection: Node makes outbound HTTP requests to a third-party URL configured by the user.

Handling:
- Wrap the HTTP call in a `try/except` that catches `requests.exceptions.RequestException` (or the specific exception from the HTTP client)
- Raise a domain execution exception (see `execution_exceptions.py` for examples like `WebhookApiFailedException`)
- Never catch bare `Exception` — let other exceptions propagate to the outer `execute_node` wrapper

Validation: Verify the exception class inherits from `BaseExceptionClass`.

### Node has multiple execution outcomes (partial success / partial failure)

Detection: The node acts on multiple records/items and some may succeed while others fail (e.g. `UPDATE_RELATED_RECORDS`, `CREATE_RELATED_RECORD`).

Handling:
- The execution method returns `(node_exec_result, node_status)` as a 2-tuple instead of just `node_exec_result`
- `node_status` is set to `NodeExecLogStatusEnum.FAILED.value` if ALL records failed, or left as `None` (defaults to DONE) if at least some succeeded
- `_execute_node_based_on_type` must unpack this tuple:
  ```python
  node_exec_result, node_status = executor.execute_...()
  ```

Validation: Confirm the dispatcher branch correctly assigns both `node_exec_result` and `node_status`.

### Node does not need a dedicated update mutation

Detection: The node has no user-editable configuration (e.g. a "delete pipeline item" action with no parameters).

Handling:
- Still define `UpdateNodeYourNodeTypeDTO(BaseUpdateNodeDTO)` with `pass` body — required for the rename flow and future-proofing
- The `update_node` method in the config interactor can immediately raise `NotImplementedError` or return the unchanged node DTO
- Do NOT omit the update storage method from the interface and implementation

Validation: Confirm `NodeStorageInterface` still has both `create_*` and `update_*` abstract methods implemented.

### Node config uses a complex nested data structure

Detection: Config requires lists of nested objects (like `FieldMappingDTO`, `HeaderDTO`), not just scalar values.

Handling:
- Define helper DTOs in `automation_workflows/interactors/nodes/dtos.py` before the Create DTO
- Serialize nested DTOs to JSON in the storage implementation before writing to `Node.exec_config`
- Deserialize from JSON in `_prep_*_dto()` helper using `json.loads`
- Never store raw Python objects in `exec_config` — always serialize to string

Validation: Confirm the storage implementation includes both serialize-on-write and deserialize-on-read logic.

### Node type is not supported in a specific workflow exec type (FOREGROUND/BACKGROUND)

Detection: The workflow engine has `exec_type` (FOREGROUND vs BACKGROUND) and some node types are restricted.

Handling:
- Add the node type to the appropriate exclusion list in `automation_workflows/constants/config.py` if applicable
- The `ValidateNodeCreationInteractor` already checks this list — do not add the check manually in the config interactor

Validation: Search `config.py` for `NodeNotSupportedInAutomationWorkflowExecType` to find the exclusion lists.
