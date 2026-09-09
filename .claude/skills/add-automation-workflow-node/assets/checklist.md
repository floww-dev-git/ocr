# New Node Implementation Checklist

Copy this and use it to track progress for each new node.

Node type being added: `NodeType.___________`

## Phase 1: Registration and DTOs

- [ ] `NodeType.YOUR_NODE_TYPE = "YOUR_NODE_TYPE"` added in `constants/enum.py`
- [ ] `NodeType.YOUR_NODE_TYPE.value` added to `action_node_types()` classmethod in `constants/enum.py`
- [ ] `YourNodeTypeNodeResponseKeys` enum class added in `constants/enum.py`
- [ ] New node type added to ALL applicable maps in `constants/config.py` (read full file, check every dict)
- [ ] `CreateNodeYourNodeTypeDTO(BaseCreateNodeDTO)` in `interactors/nodes/dtos.py`
- [ ] `UpdateNodeYourNodeTypeDTO(BaseUpdateNodeDTO)` in `interactors/nodes/dtos.py`
- [ ] `YourNodeTypeNodeDTO(BaseNodeDTO)` in `interactors/nodes/dtos.py`
- [ ] `dtos.YourNodeTypeNodeDTO` added to `NODE_DTO` union in `interactors/nodes/__init__.py`
- [ ] `YourNodeTypeNodeExecLogResultDTO` in `interactors/execution/dtos.py`
- [ ] `YourNodeTypeNodeExecLogDTO(BaseNodeExecLogDTO)` in `interactors/execution/dtos.py`
- [ ] `YourNodeTypeNodeExecLogDTO` added to `NODE_EXEC_LOG_DTOS_UNION`

## Phase 2: Storage Layer

- [ ] `create_node_your_node_type(...)` abstract method in `NodeStorageInterface`
- [ ] `update_node_your_node_type(...)` abstract method in `NodeStorageInterface`
- [ ] `create_node_your_node_type(...)` concrete implementation in `NodeStorageImpl`
- [ ] `update_node_your_node_type(...)` concrete implementation in `NodeStorageImpl`
- [ ] `_get_your_node_type_node_dto()` deserializer (JSON → DTO) in `NodeStorageImpl`
- [ ] `_get_your_node_type_node_exec_config()` serializer (DTO → JSON) in `NodeStorageImpl`
- [ ] Entry added to DTO getter map in `NodeStorageImpl` (~line 177)
- [ ] Entry added to exec config getter map in `NodeStorageImpl` (~line 210)

## Phase 3: Configuration Interactor

- [ ] `YourNodeTypeNodeInteractor(BaseNodeInteractor)` file created
- [ ] `create_node(user_id, node_dto)` implemented
- [ ] `update_node(user_id, update_node_dto)` implemented
- [ ] `_validate_creation(...)` calls `ValidateNodeCreationInteractor`
- [ ] `_validate_node_config(...)` raises domain exceptions for invalid config
- [ ] `_get_node_config_status(...)` computes `CONFIGURED` vs `PARTIALLY_CONFIGURED`
- [ ] `_get_create_node_extra_info_dto(...)` sets correct order + filter_set_id
- [ ] `update_parent_node_result()` called before storage create
- [ ] `update_child_parent_node()` called after storage create
- [ ] Domain exceptions added in `exceptions/node_exceptions.py`

## Phase 4: Execution Interactor

- [ ] `ExecuteYourNodeTypeInteractor` (or inline method) created
- [ ] Execution method accepts only the field-response maps it actually uses
- [ ] Returns a plain `Dict` with result keys defined using `YourNodeTypeNodeResponseKeys`
- [ ] External service calls wrapped in specific exception handling (not bare `except`)
- [ ] `elif node_type == NodeType.YOUR_NODE_TYPE.value:` branch added in `_execute_node_based_on_type`
- [ ] `@staticmethod` wrapper method `execute_your_node_type_node(...)` added at bottom of `ExecuteNodeInteractor`
- [ ] Correct field-response map variant passed to executor
- [ ] `changed_pipeline_item_fields` extended if node modifies field values
- [ ] `node_status` unpacked if executor returns 2-tuple
- [ ] Entry added to converter map in `node_exec_logs_interactor.py` (~line 138)
- [ ] `_transform_your_node_type_node_log_dto()` method added in `node_exec_logs_interactor.py`
- [ ] Entry added to converter map in `get_field_ids_in_nodes_config.py` (~line 60)
- [ ] `_get_your_node_type_node_field_ids()` method collects BOTH left-side (target) AND right-side (source) field IDs
- [ ] Entry added to converter map in `get_latest_lead_field_ids.py` (~line 61)
- [ ] `_get_your_node_type_node_latest_lead_field_ids()` method added in `get_latest_lead_field_ids.py`
- [ ] Node-specific execution exceptions registered in `prepare_node_err_msg.py` (`isinstance` checks)
- [ ] `field_type_map` always accessed with `.get()` (never `[]`) — handles fixed payload keys like `FROM_STAGE`, `TO_STAGE`

## Phase 5: GraphQL Layer

- [ ] `YourNodeType(graphene.ObjectType)` added in `nodes/types/types.py`
- [ ] `YourNodeType` added to `Node` union in `nodes/types/types.py` (~line 937)
- [ ] `NotYourNodeTypeNodeType(graphene.ObjectType)` error type added in `nodes/types/error_types.py`
- [ ] `NodeTypesConverter` handles `YourNodeTypeNodeDTO` → `YourNodeType`
- [ ] `CreateNodeYourNodeTypeParams(BaseCreateNodeParams)` defined
- [ ] `CreateNodeYourNodeTypeResponse(graphene.Union)` defined with all error types
- [ ] `CreateNodeYourNodeType(graphene.Mutation)` wired to interactor
- [ ] `UpdateNodeYourNodeTypeParams`, `UpdateNodeYourNodeTypeResponse`, `UpdateNodeYourNodeType` defined
- [ ] Both mutations registered in schema
- [ ] `YourNodeTypeNodeExecLogResult(graphene.ObjectType)` added in `automation_workflows/types/types.py`
- [ ] `YourNodeTypeNodeExecLog(graphene.ObjectType)` added in `automation_workflows/types/types.py`
- [ ] `YourNodeTypeNodeExecLog` added to `NODE_EXEC_LOG_GQL_TYPES` union
- [ ] Transformer entry added to converter map in `automation_workflows/utils.py` (~line 78)
- [ ] `_transform_your_node_type_node_log_dto()` method added in `automation_workflows/utils.py`

## Phase 6: Tests

- [ ] `YourNodeTypeNodeFactory` model factory added in `tests/factories/models.py`
- [ ] `CreateNodeYourNodeTypeDTOFactory` added in `tests/factories/interactor_dtos/node_dtos.py`
- [ ] `UpdateNodeYourNodeTypeDTOFactory` added in `tests/factories/interactor_dtos/node_dtos.py`
- [ ] `YourNodeTypeNodeDTOFactory` added in `tests/factories/interactor_dtos/node_dtos.py`
- [ ] Config interactor tests written (`test_your_node_type_node.py`)
  - [ ] `test_create_node_success`
  - [ ] `test_create_node_invalid_config_raises_exception`
  - [ ] `test_update_node_success`
  - [ ] `test_update_node_wrong_type_raises_exception`
  - [ ] `test_get_node_config_status_configured`
  - [ ] `test_get_node_config_status_partially_configured`
- [ ] Execution interactor tests written (`test_execute_your_node_type.py`)
  - [ ] `test_execute_success`
  - [ ] `test_execute_service_failure_propagates`
- [ ] All tests pass: `pytest -v --no-migrations`

## Phase 7: Code Quality

- [ ] No bare `except Exception:` used anywhere
- [ ] All enum values passed as `.value` in DTOs
- [ ] `# noinspection PyTypeChecker` on lines assigning enum `.value` to enum-typed attribute
- [ ] No storage calls inside loops
- [ ] No `print`, `logger.info`, or `logging` in business logic
- [ ] All public methods have type hints on parameters and return type
- [ ] All files within 200-line target (500 hard limit)
- [ ] All methods within 50-line limit
