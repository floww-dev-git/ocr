---
name: configio-export-guide
description: Guide through configio export implementation including schema definition, export interactors, entity handlers, and cross-app service interfaces. Use when creating configio export modules, schema engine usage, entity handlers for data retrieval, or cross-app service interfaces.
user-invocable: false
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Configio Export Guide

Expert guidance for implementing configio **export** functionality following established patterns in `bps/configio/` and `tdr/`.

**Note**: Import flow is out of scope. Entity handler methods used only by import should raise `NotImplementedError`.

## Architecture Prerequisites (Read Before Implementing)

ConfigIO export features follow a strict two-app split between the IO orchestrator (`bps`) and the **app that owns the entity's domain logic** (the "owning app" — `sales_crm_core`, `tdr`, `portals`, `rules_engine`, etc.):

| What | Where |
|---|---|
| Thin export_interactor.py wrapper | `bps/configio/<module>/` |
| Actual export logic (storage reads, DTO assembly) | `<owning_app>/interactors/configio/<entity>/export_interactor.py` |
| Bridge method | `<owning_app>/app_interfaces/service_interface.py` |
| Pass-through adapter | `bps/adapters/<owning_app>_service.py` |

**Hard rules:**
1. `bps/configio/<module>/export_interactor.py` must only call `get_service_adapter().<owning_app>_service.export_<entity>()`
2. Never access the owning app's storages or models directly from bps
3. Export logic (storage reads, DTO prep) lives in the owning app, not bps

See `clean-architecture.md` -> `## ConfigIO Architecture` for the full decision tree.

## Implementation Phases

### Phase 1: Discovery & Mapping Validation

Errors here cascade through all subsequent phases. For each entity, validate the three-step mapping chain:

1. **DTO Field -> JSON Key** (in `EntityConverter.convert_dto_to_json()`)
2. **JSON Key -> CSV Column Name** (in schema definition via `csv_column_name`)
3. **CSV Output** (via `SchemaEngine.transform_flat_data_to_csv()`)

Verify: JSON Keys enum has all keys, converter uses correct keys, schema has matching properties with `csv_column_name`, type transformations handled (datetime, boolean, lookups).

### Phase 2: Schema & Constants Definition

- Create JSON Keys enums in `bps/configio/{module}/constants/json_keys.py`
- Define schema with `csv_column_name` for each property in `bps/configio/{module}/schema.py`

See [Schema Definition Patterns](references/schema-patterns.md) for property types, constraints, and complete examples.

### Phase 3: Entity Handlers & Converters (Cross-App Only)

Skip if data is within the same app.

Every configio entity has an `EntityHandlerInterface` implementation. The same handler class serves both export and import — for export, only `get_entity_jsons()` is invoked; import-only methods may `raise NotImplementedError()` in export-only handlers.

- The handler lives in the **app that owns the entity's domain logic** (not always `sales_crm_core` — see [EntityHandler Interface](references/entity-handler-interface.md) for verified host apps including `tdr`, `bps`, `portals`, `rules_engine`)
- Implement `EntityConverter.convert_dto_to_json()` in `<owning_app>/interactors/configio/<entity>/entity_converter.py`
- Implement `<Entity>Handler.get_entity_jsons()` following the contract
- Expose the handler via the owning app's `app_interfaces/service_interface.py`, called from `bps/configio/<module>/` only through the service adapter

See [EntityHandler Interface](references/entity-handler-interface.md) for the full contract, host-app rules, and wiring pattern.
See [Entity Handler Patterns](references/entity-handler-patterns.md) for converter implementation and export-specific examples.

### Phase 4: Export Interactor (Data Gathering)

- Implement in `bps/configio/{module}/export_interactor.py`
- Gather data from service adapters in parent -> child order
- Return `Dict[entity_name, List[json_records]]`

See [Export Interactor Patterns](references/export-patterns.md) for data gathering and CSV transformation.

### Phase 5: CSV Export Interactor (Transformation & Output)

- Use `SchemaEngine.transform_flat_data_to_csv()` to map JSON keys to CSV column names
- Write CSV files using `CSVWriter`
- Return typed DTO with all records

See [Export Interactor Patterns](references/export-patterns.md) for CSV export implementation.

## Architecture Overview

```
ExportInteractor (Data Gathering)
  -> Uses service adapters or entity handlers
  -> Returns Dict[str, List[Dict]] with entity names as keys

ExportCSVInteractor (CSV Transformation)
  -> Calls ExportInteractor
  -> SchemaEngine.transform_flat_data_to_csv()
  -> CSVWriter for file output
```

### Cross-App Communication
```
bps/configio/.../export_interactor.py
  -> BPS Adapter -> ServiceInterface (other app)
    -> EntityHandler.get_entity_jsons()
      -> GetEntities interactor -> EntityConverter.convert_dto_to_json()
```

## Key Reference Files

| Component | File Path |
|-----------|-----------|
| SchemaEngine | `bps/configio/core/schema_engine/schema_engine.py` |
| EntityHandlerInterface | `bps/configio/core/io_engine/entity_interface.py` |
| StageTransitionHandler (canonical handler example) | `sales_crm_core/interactors/configio/stage_transitions/stage_transition_handler.py` |
| CSVWriter | `bps/configio/core/csv_utils/csv_writer.py` |
| TDR Bank Export (Simple) | `bps/configio/tdr_bank/export_interactor.py` |
| Pipeline Export (Complex) | `bps/configio/pipeline/export_interactor.py` |

## Detailed Reference Guides

- [Schema Definition Patterns](references/schema-patterns.md) - Property types, constraints, foreign keys
- [Export Interactor Patterns](references/export-patterns.md) - Data gathering and CSV transformation
- [EntityHandler Interface](references/entity-handler-interface.md) - Shared handler contract (export + import), host-app rules, cross-app wiring
- [Entity Handler Patterns](references/entity-handler-patterns.md) - Cross-app data retrieval and converters
- [Complete Examples](references/complete-examples.md) - Full module implementations
