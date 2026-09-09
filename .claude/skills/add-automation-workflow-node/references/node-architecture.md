# Node Architecture Reference

## Key Files Map

| Concern | File |
|---|---|
| Node type enum + `action_node_types()` | `automation_workflows/constants/enum.py` — `NodeType` (~line 87 for classmethod) |
| Node response keys enums | `automation_workflows/constants/enum.py` — `*NodeResponseKeys` classes |
| Trigger-event compatibility maps | `automation_workflows/constants/config.py` — 10+ dicts mapping trigger combos to supported node types |
| Config DTOs | `automation_workflows/interactors/nodes/dtos.py` |
| NODE_DTO union + NodeResultDTO | `automation_workflows/interactors/nodes/__init__.py` |
| Config base class | `automation_workflows/interactors/nodes/base_node.py` — `BaseNodeInteractor` |
| Config interactors | `automation_workflows/interactors/nodes/<node_type>_node.py` |
| Storage interface | `automation_workflows/interactors/storage_interfaces/node_storage_interface.py` |
| Storage implementation | `automation_workflows/storages/node_storage_impl.py` |
| Storage DTO getter map | `automation_workflows/storages/node_storage_impl.py` ~line 177 |
| Storage exec config getter map | `automation_workflows/storages/node_storage_impl.py` ~line 210 |
| Execution dispatch | `automation_workflows/interactors/execution/execute_node_interactor.py` — `_execute_node_based_on_type` |
| Action executors | `automation_workflows/interactors/execution/action_node/execute_<name>.py` |
| Execution DTOs | `automation_workflows/interactors/execution/dtos.py` |
| Exec log transformation | `automation_workflows/interactors/execution/node_exec_logs_interactor.py` — converter map ~line 138 |
| Field ID resolution (config) | `automation_workflows/interactors/configuration/automation_workflows/get_field_ids_in_nodes_config.py` — converter map ~line 60 |
| Field ID resolution (lead) | `automation_workflows/interactors/configuration/automation_workflows/get_latest_lead_field_ids.py` — converter map ~line 61 |
| Node DB model | `automation_workflows/models/node.py` |
| Action node DB model | `automation_workflows/models/action_node.py` |
| Node exceptions | `automation_workflows/exceptions/node_exceptions.py` |
| Execution exceptions | `automation_workflows/exceptions/execution_exceptions.py` |
| Error message handler | `automation_workflows/interactors/execution/prepare_node_err_msg.py` — `isinstance()` chain for exception → user message |
| Trigger-event maps | `automation_workflows/constants/config.py` — `SUPPORTED_EVENT_BASED_TRIGGERS_MAP` (~line 355), `SUPPORTED_SCHEDULED_TRIGGERS_MAP` (~line 592) |
| Trigger payload keys | `automation_workflows/constants/enum.py` — `TriggerPayloadKey` (FROM_STAGE, TO_STAGE, etc.) |
| Model test factories | `automation_workflows/tests/factories/models.py` |
| DTO test factories | `automation_workflows/tests/factories/interactor_dtos/node_dtos.py` |
| GraphQL node types + Node union | `sales_crm_graphql/automation_workflows/nodes/types/types.py` — `Node` union ~line 937 |
| GraphQL error types | `sales_crm_graphql/automation_workflows/nodes/types/error_types.py` |
| GraphQL create mutations | `sales_crm_graphql/automation_workflows/nodes/mutations/create_nodes/` |
| GraphQL update mutations | `sales_crm_graphql/automation_workflows/nodes/mutations/update_nodes/` |
| NodeTypesConverter | `sales_crm_graphql/automation_workflows/nodes/resolvers/node_types_converter.py` |
| GraphQL exec log types + union | `sales_crm_graphql/automation_workflows/automation_workflows/types/types.py` — `NODE_EXEC_LOG_GQL_TYPES` union |
| GraphQL exec log transformer | `sales_crm_graphql/automation_workflows/automation_workflows/utils.py` — converter map ~line 78 |

## Node DB Schema

`Node` model (single table for all node types):
- `id` — UUID CharField PK
- `name` — nullable name shown in UI
- `automation_workflow_exec_config` — FK to `AutomationWorkFlowExecConfig` (CASCADE)
- `node_type` — CharField validated against `NodeType` enum
- `config_status` — `PARTIALLY_CONFIGURED` or `CONFIGURED`
- `order` — integer for tree ordering
- `parent_node` — self-FK (SET_NULL), nullable
- `parent_node_result` — `TRUE`/`FALSE`, which branch from parent CONDITION we are on
- `exec_config` — TextField (JSON blob), stores serialized node-specific config
- `filter_set` — FK to `FilterSet` (SET_NULL), nullable, only needed for condition/filter nodes

`ActionNode` model (1:1 with `Node`):
- `id` — UUID CharField PK
- `node` — OneToOneField to `Node` (CASCADE)
- `action_type` — `ActionTypeEnum` (legacy, only 6 values: UPDATE_LEAD, CREATE_ACTIVITY, CREATE_TASK, CALL_API, CLEAR_UNDONE_LEAD_TASKS, SEND_DATA_TO_SEGMENT)
- `exec_config` — TextField (JSON blob), additional config

Note: `ActionNode` is a legacy model. New nodes do NOT need to create an `ActionNode` row. Config lives entirely in `Node.exec_config`.

## Execution Flow (detailed)

```
ExecuteAutomationWorkflowInteractor.execute()
  └── ExecuteNodeInteractor.execute_node(exec_req_dto, ...)
        ├── Create initial NodeExecLog (DynamoDB + PostgreSQL) with PROCESSING status
        ├── Call _execute_node_based_on_type(exec_req_dto, node_exec_log_dto)
        │     └── elif node_type == NodeType.YOUR_TYPE.value:
        │           └── YourExecutor().execute_your_node(...)
        │                 └── Returns (node_exec_result, [node_status], [changed_fields])
        ├── On exception:
        │     ├── If CONDITION: raise ConditionNodeExcFailedException (halts branch)
        │     └── Otherwise: append to failed_node_ids, append AwFailedNodeDTO, continue
        ├── Update NodeExecLog with result + DONE/FAILED status
        └── Recurse into child nodes via child_nodes_map[(node_id, node_result)]
```

`node_result` returned from `_execute_node_based_on_type`:
- `NodeResultEnum.TRUE` or `NodeResultEnum.FALSE` — only CONDITION nodes set this
- `None` — all action nodes; the dispatch uses `None` as the key to find children
- This means: all action nodes chain via `child_nodes_map[(node_id, None)]`

## ExecConfig Maps (execution context)

`AutomationWorkflowExecConfigMapsDTO` is built once per workflow execution and passed to every node:

| Attribute | Type | Contains |
|---|---|---|
| `root_node_ids` | `List[str]` | Entry point node IDs for this exec config |
| `child_nodes_map` | `Dict[(node_id, NodeResultEnum), List[str]]` | Which children to execute given a node result |
| `node_dto_map` | `Dict[str, NODE_DTO]` | All node DTOs keyed by node_id |
| `entity_filters_map` | `Dict[str, EntityFiltersDTO]` | FilterSet data for condition nodes |
| `field_type_map` | `Dict[str, FieldType]` | Field type per field_id |
| `latest_lead_fields_maps_dto` | `LatestLeadFieldResponseMapsDTO` | Multiple views of the pipeline item's field values |
| `trigger_payload_maps_dto` | `TriggerPayloadMapsDTO` | Multiple views of the event trigger payload |
| `user_properties_maps_dto` | `UserPropertyFieldResponseMapsDTO` | Assignee-scoped field values |

The `latest_lead_fields_maps_dto` has multiple response formats for the same data:
- `internal_response_map` — UUID/raw DB values (use for user ID lookups, pipeline IDs)
- `third_party_response_map` — sanitized strings for external APIs
- `obj_response_map` — full Python objects (`FIELD_RESPONSE_TYPE`) for complex processing
- `formatted_response_map` — human-readable display values
- `document_formatted_response_map` — specialized for document variable substitution

## NodeConfigStatus Logic

`CONFIGURED` — all required fields for this node's action are present and valid.
`PARTIALLY_CONFIGURED` — at least one required field is missing or invalid.

The UI uses this to show a warning indicator on the node. Workflows can be published with `PARTIALLY_CONFIGURED` nodes but will fail at runtime.

Compute this deterministically in `_get_node_config_status()` using truthiness of required fields. Never hardcode the status.

## How `exec_config` is populated

When `create_workflow_node(NodeDTO)` is called in the storage implementation:

1. The implementation builds a JSON string from the node-specific config fields
2. This JSON is stored in `Node.exec_config`
3. At publish time, the EDITABLE config is cloned to a PUBLISHED copy — `exec_config` is cloned as-is
4. At execution time, the node DTO is hydrated from `Node.exec_config` JSON

This means the storage implementation must:
- On create/update: serialize config fields → JSON string → `Node.exec_config`
- On read (`_prep_*_dto()`): deserialize JSON → populate DTO fields

## GraphQL Interface Patterns

All GraphQL types in this domain use interfaces for shared fields:

| Type category | Interface | Provides |
|---|---|---|
| Node config types | `BaseNode` | `node_id`, `name`, `node_type`, `config_status`, `order`, `parent_node_id`, `parent_node_result`, `automation_workflow_exec_config_id` |
| Exec log types | `BaseNodeExecLog` | `node_exec_log_id`, `node_id`, `status`, `failure_reason` |
| Error types | `GraphQLBaseError` | standard error fields |

New GraphQL types use `class Meta: interfaces = (InterfaceName,)` and only define node-specific fields. Do not manually list interface fields.

## Exec Log Data Flow (end-to-end)

```
ExecuteNodeInteractor.execute_node()
  → node_exec_result (Dict) stored in NodeExecutionLogDTO.result
  → NodeExecLogsInteractor._transform_*_node_log_dto()
    → reads raw Dict from NodeExecutionLogDTO.result
    → uses _get_base_node_dto() for base fields
    → uses **base_node_dto.__dict__ spread pattern
    → returns typed *NodeExecLogDTO (e.g. CallWebhookNodeExecLogDTO)
  → GraphQL utils._transform_*_node_log_dto()
    → reads typed DTO fields
    → returns GraphQL ObjectType (e.g. CallWebhookNodeExecLog)
```

Key: the backend transformer receives `(node_log_dto: NodeExecutionLogDTO, failure_reason: Optional[str])`. The GraphQL transformer receives the typed exec log DTO.

## Static Wrapper Pattern in ExecuteNodeInteractor

The `elif` branches in `_execute_node_based_on_type` call `self.execute_*_node(...)` which are `@staticmethod` methods at the bottom of `ExecuteNodeInteractor`. Each static wrapper does the deferred import and delegates to the concrete executor:

```python
@staticmethod
def execute_your_node_type_node(...) -> Dict:
    from automation_workflows.interactors.execution.action_node.execute_your_node_type import (
        ExecuteYourNodeTypeInteractor,
    )
    interactor = ExecuteYourNodeTypeInteractor()
    return interactor.execute_your_node_type(...)
```

All existing nodes use this pattern. The `elif` branch calls `self.execute_*()`, not the executor class directly.

## Validated patterns from existing nodes

**Simplest node** (no external calls, no field maps): `RemoveFromPipelineNodeInteractor`
- Config: 3 boolean fields in exec_config
- Execution: calls `sales_crm_service.remove_from_pipeline()`

**Field-mapping node** (reads pipeline item fields, applies transforms): `UpdateLeadNodeInteractor`
- Config: list of `FieldMappingParamsDTO`, optional clear list
- Execution: calls `sales_crm_service.update_lead_field_responses_bulk()`

**External HTTP call node**: `ExecuteCallWebhookNodeInteractor`
- Config: endpoint URL, headers, payload mapping
- Execution: builds request from field maps, calls `requests.post/get`, raises `WebhookApiFailedException` on HTTP error
- Return type: `Dict` (single return)

**Partial-failure node**: `ExecuteGenerateDocumentNodeInteractor`
- Config: document_template_id, title, variable_mappings, copy_document_url_to_field
- Execution: generates document via plugin, then optionally copies URL to a field
- Return type: `Tuple[Dict, NodeExecLogStatusEnum]` — document gen succeeds but field copy may fail independently
- Uses `document_formatted_response_map` (not `formatted_response_map`)

**Notification node**: `ExecuteSendPipelineItemNotificationInteractor`
- No constructor injection — services via `@property` with deferred imports
- Returns a plain dict with result keys defined as an enum (`NotificationNodeResponseKeys`)
