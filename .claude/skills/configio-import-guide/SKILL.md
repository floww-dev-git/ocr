---
name: configio-import-guide
description: Guide through configio import implementation including CSV parsing, filtering, CSV-to-JSON conversion, schema validation, diff-based action generation, and action execution. Use when creating configio import modules, implementing ImportStore subclasses, CSV-to-JSON converters, action generators, run action handlers, or data stores.
user-invocable: false
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Configio Import Guide

Expert guidance for implementing configio **import** functionality following established patterns in `bps/configio/`.

**Note**: Export flow is out of scope. Refer to `configio-export-guide` for export. Import and export **share** schema definitions, JSON keys, and constants.

## Architecture Prerequisites (Read Before Implementing)

ConfigIO import features follow a strict two-app split between the IO orchestrator (`bps`) and the **app that owns the entity's domain logic** (the "owning app" — `sales_crm_core`, `tdr`, `portals`, `rules_engine`, etc.). Before writing any code, confirm placement:

| What | Where |
|---|---|
| ImportStore subclass, action_generators, run_actions_handlers, thin import_interactor | `bps/configio/<module>/` |
| EntityHandlerInterface impl, checkers, create/update interactors | `<owning_app>/interactors/configio/<entity>/` (host app varies per entity) |
| Bridge methods | `<owning_app>/app_interfaces/service_interface.py` + `bps/adapters/<owning_app>_service.py` |

**Hard rules:**
1. Always use `ImportInteractor(import_store=store).execute()` -- never write custom import loops
2. run_actions_handlers access the owning app ONLY via `get_service_adapter().<owning_app>_service.<method>()`
3. Checkers receive typed DTOs -- never `asdict()` or dict key access
4. Register action_generators with `@register_action_generator`, handlers with `@register_bps_template_run_action`

See `clean-architecture.md` -> `## ConfigIO Architecture` for the full decision tree.

## Implementation Phases

### Phase 1: CSV Parsing & Filtering

- Read CSV files via `CSVReader`
- Filter rows/columns via `SheetFilterParamsDTO`
- Apply optional CSV transformations via `CSVTransformer`

See [CSV Processing Patterns](references/csv-processing-patterns.md) for reading, filtering, and transformation details.

### Phase 2: CSV-to-JSON Conversion (Reverse of Export)

The reverse mapping chain: **CSV Column Name -> JSON Key -> DTO Field -> Database Entity**

- Map CSV column names to JSON keys via `SchemaEngine.get_property_id()`
- Restructure flat CSV records by entity name
- Validate foreign key references

Implement `CsvToJsonConverter` with two steps: restructure by entity name, then map columns to property IDs.

See [ImportStore Patterns](references/import-store-patterns.md) for converter implementation.

### Phase 3: Validation & Transformation

Orchestrated by `ImportStore.transform_to_json_data()`:
1. `convert_csv_to_json_data()` - CSV columns to JSON keys
2. `_check_foreign_key_references()` - FK validation
3. `convert_json_data_to_nested_data()` - flat to parent-child grouping
4. `SchemaEngine.validate_data()` - schema validation
5. `SchemaEngine.transform_data()` - type transformations
6. `convert_nested_data_to_flat_data()` - back to flat for action generation

See [ImportStore Patterns](references/import-store-patterns.md) for the 6 abstract methods to implement.

### Phase 4: Action Generation (Diff-Based)

- Export existing config via `get_existing_config()` (calls export interactor)
- Compare old vs new using `JsonComparisonService`
- Generate CREATE/UPDATE actions per entity type
- Register generators via `@register_action_generator` decorator
- Implement `build_entity_dto()` (reverse of export's `convert_dto_to_json()`)

See [Action Generation Patterns](references/action-generation-patterns.md) for registry, generators, and `build_entity_dto()`.

### Phase 4.5: Entity Handler (Domain Side)

Action generators produce `ChangeConfigActionDTO`s. Run-action-handlers in `bps/configio/<module>/run_actions_handlers/` invoke those actions via the service adapter — but the actual create/update/check work happens in an `EntityHandlerInterface` implementation that lives in the **app that owns the entity's domain logic**.

- The handler is NOT in `bps/configio/<module>/`. It lives in the owning app (e.g., `sales_crm_core`, `tdr`, `portals`, `rules_engine`, or `bps/interactors/` for bps-domain entities)
- For import, the handler implements: `convert_json_to_dto`, `validate`, `run_checks_for_create`, `run_checks_for_update`, `create`, `update`. The export-only `get_entity_jsons` may `raise NotImplementedError()` in import-only handlers
- The owning app exposes the handler through its `app_interfaces/service_interface.py` (e.g., `sales_crm_core/app_interfaces/service_interface.py`). `bps/configio/<module>/run_actions_handlers/` never imports the handler directly — only via `get_service_adapter().<owning_app>_service.<method>()`
- `validate` is invoked before action-type-specific checks; `run_checks_for_*` returns `List[RunActionErrorDTO]` for the all-or-nothing orchestrator
- Inside `create`/`update`, delegate to existing create/update interactors in the owning app via deferred imports

Canonical example: `StageTransitionHandler` at `sales_crm_core/interactors/configio/stage_transitions/stage_transition_handler.py`.

See [EntityHandler Interface](../configio-export-guide/references/entity-handler-interface.md) for the full contract, host-app rules, and cross-app wiring.

### Phase 5: Action Validation & Execution

All-or-nothing pattern via `RunActionsOrchestrator`:
1. `run_all_checks(actions)` - validate every action, collect all errors
2. `execute_all(actions)` - execute only if zero errors
3. Export errors to `errors.csv` on failure

Register handlers via `@register_bps_template_run_action(entity_type, action_type)`.

See [Run Actions Patterns](references/run-actions-patterns.md) for handler implementation.

## ImportStore: The Core Abstraction

`ImportStore` drives Phases 2-3 with 6 abstract methods:

| Method | Purpose |
|--------|---------|
| `generate_action_entity_types()` | Ordered list of `GenerateEntityActionEnum` values |
| `convert_csv_to_json_data()` | CSV column names -> JSON keys |
| `convert_json_data_to_nested_data()` | Flat -> parent-child hierarchy |
| `convert_nested_data_to_flat_data()` | Nested -> flat after validation |
| `data_store()` | In-memory DataStore for lookups |
| `get_existing_config()` | Export current DB state for diff |

## Full Import Pipeline

**Runs inside `@transaction.atomic()`** -- any failure rolls back all DB changes.

```
ImportInteractor.execute()
  1. _parse_csv_files()           -> CSVReader
  2. filter_csv_records()         -> SheetFilterParamsDTO
  3. _apply_csv_transformations() -> CSVTransformer (optional)
  4. transform_to_json_data()     -> Phases 2-3
  5. _handle_validation_errors()  -> Reports
  6. data_store()                 -> In-memory lookups
  7. _create_change_actions()     -> Phase 4 (diff)
  8. _execute_actions()           -> Phase 5 (all-or-nothing)
```

## Key Reference Files

| Component | File Path |
|-----------|-----------|
| ImportInteractor | `bps/configio/core/io_engine/import_interactor.py` |
| ImportStore (ABC) | `bps/configio/core/io_engine/import_store.py` |
| SchemaEngine | `bps/configio/core/schema_engine/schema_engine.py` |
| EntityHandlerInterface | `bps/configio/core/io_engine/entity_interface.py` |
| StageTransitionHandler (canonical handler example) | `sales_crm_core/interactors/configio/stage_transitions/stage_transition_handler.py` |
| ActionGeneratorRegistry | `bps/configio/core/generate_actions_utils/action_generator_registry.py` |
| RunActionsOrchestrator | `bps/configio/bps_template/run_actions_handlers/run_actions.py` |
| TDR Bank ImportStore | `bps/configio/tdr_bank/import_store.py` |

## Detailed Reference Guides

- [CSV Processing Patterns](references/csv-processing-patterns.md) - CSV reading, filtering, transformations
- [ImportStore Patterns](references/import-store-patterns.md) - ImportStore, CSV-to-JSON, flat-to-nested
- [Action Generation Patterns](references/action-generation-patterns.md) - Action generators, registries, diff engine
- [Run Actions Patterns](references/run-actions-patterns.md) - Action handlers, validation, execution
- [EntityHandler Interface](../configio-export-guide/references/entity-handler-interface.md) - Shared handler contract (export + import), host-app rules, cross-app wiring
- [Complete Examples](references/complete-examples.md) - Full Pipeline + TDR Bank import examples
