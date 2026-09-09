# Complete Import Examples

## Example 1: Pipeline Import (Simple)

### Directory Structure

```
bps/configio/pipeline/
├── __init__.py
├── schema.py                          # Shared with export
├── constants/
│   └── json_keys.py                   # Shared with export
├── import_interactor.py               # Top-level entry point
├── import_store.py                    # ImportStore subclass
├── data_store.py                      # In-memory DataStore
├── json_converters/
│   └── csv_to_json_converter.py       # CsvToJsonConverter
├── interactors/
│   └── transform_pipeline_json_data_interactor.py  # Flat-to-nested
├── action_generators/
│   ├── __init__.py                    # Imports trigger registration
│   ├── generate_actions_for_pipeline.py
│   ├── generate_action_for_stage.py   # Note: singular "action"
│   ├── generate_actions_for_stage_transition.py
│   └── ...                            # (11 generator files total)
├── run_actions_handlers/
│   ├── __init__.py                    # Imports trigger registration
│   ├── pipeline_create_action.py
│   ├── pipeline_update_action.py
│   ├── stage_config_create_action.py  # Note: "stage_config", not "stage"
│   ├── stage_config_update_action.py
│   └── ...                            # (22 handler files total)
├── export_interactor.py               # Used by get_existing_config()
└── export_csv_interactor.py
```

### ImportPipelinesInteractor (Top-Level)

**File**: `bps/configio/pipeline/import_interactor.py`

```python
class ImportPipelinesInteractor:
    def import_pipelines(
        self, csv_path_map: Dict[str, str], pipeline_item_template_id: str
    ) -> ImportResultDTO:
        import_store = PipelineImportStore(
            pipeline_item_template_id=pipeline_item_template_id
        )
        interactor = ImportInteractor(import_store=import_store)
        return interactor.execute(csv_path_map=csv_path_map)
```

This is the simplest form: create ImportStore, pass to ImportInteractor, call execute. No pre-processing needed.

### PipelineImportStore

**File**: `bps/configio/pipeline/import_store.py`

```python
import bps.configio.pipeline.action_generators   # noqa: F401 — trigger registration
import bps.configio.pipeline.run_actions_handlers  # noqa: F401

class PipelineImportStore(ImportStore):
    def __init__(self, pipeline_item_template_id: str):
        super().__init__(schema=BPS_PIPELINES_SCHEMA)
        self.pipeline_item_template_id = pipeline_item_template_id
        self._csv_to_json_converter = PipelineCsvToJsonConverter()
        self._json_data_transformer = TransformPipelineJsonDataInteractor()

    def generate_action_entity_types(self):
        return [
            GenerateEntityActionEnum.PIPELINE,
            GenerateEntityActionEnum.CONDITIONAL_ACTION_RULE,
            GenerateEntityActionEnum.APPLICATION_ID_GENERATION_CONFIG,
            GenerateEntityActionEnum.PERMIT_ORDER_ID_GENERATION_CONFIG,
            GenerateEntityActionEnum.STAGE,
            GenerateEntityActionEnum.PIPELINE_DEFAULT_STAGE,
            GenerateEntityActionEnum.GENERATE_APPLICATION_ID_CONFIG_V2,
            GenerateEntityActionEnum.GENERATE_APPLICATION_ID_CONFIG_V3,
            GenerateEntityActionEnum.STAGE_TRANSITION,
        ]

    def convert_csv_to_json_data(self, csv_records_map):
        return self._csv_to_json_converter.convert(csv_records_map=csv_records_map)

    def convert_json_data_to_nested_data(self, flat_data):
        return self._json_data_transformer.to_nested(flat_data=flat_data)

    def convert_nested_data_to_flat_data(self, nested_data):
        return self._json_data_transformer.to_flat(nested_data=nested_data)

    def data_store(self, json_data):
        return BPSPipelinesDataStore(
            json_data=json_data,
            pipeline_item_template_id=self.pipeline_item_template_id,
        )

    def get_existing_config(self, data_store):
        interactor = ExportPipelineInteractor(...)
        return interactor.get_existing_nested_data(
            pipeline_item_template_id=data_store.pipeline_item_template_id
        )
```

---

## Example 2: TDR Bank Import (Complex)

### Directory Structure

```
bps/configio/tdr_bank/
├── __init__.py
├── schema.py                          # Shared with export
├── constants/
│   └── json_keys.py                   # Shared with export
├── import_interactor.py               # Top-level with pre-processing
├── import_store.py                    # ImportStore subclass
├── data_store.py                      # In-memory DataStore with lookup maps
├── dtos.py                            # Module-specific DTOs
├── json_converters/
│   └── csv_json_to_converter.py       # CsvToJsonConverter
├── interactors/
│   └── transform_tdr_bank_json_data.py  # Flat-to-nested with domain logic
├── action_generators/
│   ├── __init__.py
│   ├── generate_actions_for_tdr_account.py
│   ├── generate_actions_for_tdr_account_transaction.py
│   ├── generate_actions_for_tdr_account_transaction_log.py
│   └── generate_actions_for_pipeline_item_remarks.py
├── run_actions_handlers/
│   ├── __init__.py
│   ├── tdr_account_create_action.py
│   ├── tdr_account_transaction_create_action.py
│   ├── tdr_account_transaction_log_create_action.py
│   ├── pipeline_item_remarks_create_action.py
│   └── pipeline_item_remarks_update_action.py
├── csvs_modifications.yaml            # CSV transformation config
├── export_interactor.py               # Used by get_existing_config()
└── export_csv_interactor.py
```

### ImportTdrBankInteractor (Top-Level with Pre-Processing)

**File**: `bps/configio/tdr_bank/import_interactor.py`

This is a complex example because it does significant pre-processing before calling `ImportInteractor`:

```python
class ImportTdrBankInteractor:
    def __init__(self, storage, custom_object_storage):
        self.storage = storage
        self.custom_object_storage = custom_object_storage
        self.csv_reader = CSVReader()

    def import_tdr_bank(self, csv_path_map, authority_wise_bank_id_map,
                         sheet_filter_params_dtos, file_no_keyword=None):
        # Pre-processing: build lookup maps
        bank_ids = list(authority_wise_bank_id_map.values())
        account_no_wise_account_id_map = self._get_account_no_wise_account_id_map(bank_ids)
        application_id_to_file_no_map = self._get_application_id_to_file_no_map(
            csv_path_map, file_no_keyword
        )
        application_id_to_pipeline_item_id_map = (
            self._get_application_id_to_pipeline_item_id_map(application_id_to_file_no_map)
        )
        self._update_sheet_filter_params_dtos(
            sheet_filter_params_dtos, application_id_to_file_no_map,
            application_id_to_pipeline_item_id_map,
        )
        officer_id_to_user_id_map = self._get_officer_id_to_user_id_map(csv_path_map)

        # Create ImportStore with all lookup maps
        import_store = TdrBankImportStore(
            authority_wise_bank_id_map=authority_wise_bank_id_map,
            account_no_wise_account_id_map=account_no_wise_account_id_map,
            application_id_to_file_no_map=application_id_to_file_no_map,
            application_id_to_pipeline_item_id_map=application_id_to_pipeline_item_id_map,
            officer_id_to_user_id_map=officer_id_to_user_id_map,
        )

        # Load CSV transformation config from YAML
        csv_transformation_config_map = self._get_csv_transformation_config_map()

        # Execute the standard import pipeline
        interactor = ImportInteractor(import_store=import_store)
        return interactor.execute(
            csv_path_map=csv_path_map,
            sheet_filter_params_dtos=sheet_filter_params_dtos,
            csv_transformation_config_map=csv_transformation_config_map,
        )
```

### Key Differences from Pipeline Import

| Aspect | Pipeline (Simple) | TDR Bank (Complex) |
|--------|-------------------|-------------------|
| Pre-processing | None | Builds 5 lookup maps from CSV/DB |
| ImportStore args | 1 param | 5 pre-fetched maps |
| CSV transformations | None | YAML-based config |
| Sheet filtering | None | Dynamic filter updates |
| Nested structure | Stages inside pipelines | Logs -> Transactions -> Accounts |
| DataStore | Simple field mappings | Multiple lookup maps + registration |

---

## New Module Creation Checklist

When creating a new configio import module, follow these steps in order:

### Step 1: Verify Shared Components Exist

Shared with export — check that these already exist:
- [ ] Schema definition (`schema.py`) with `csv_column_name` on each property
- [ ] JSON keys enums (`constants/json_keys.py`)
- [ ] Export interactor (needed by `get_existing_config()`)

If export doesn't exist yet, implement it first using the `configio-export-guide` skill.

### Step 2: Create CsvToJsonConverter

**File**: `bps/configio/{module}/json_converters/csv_to_json_converter.py`

```python
class ModuleCsvToJsonConverter:
    def __init__(self):
        self._schema_engine = SchemaEngine(schema=MODULE_SCHEMA)

    def convert(self, csv_records_map):
        csv_records_map = self._transform_csv_records_to_module_json_structure(csv_records_map)
        json_data = self._transform_csv_column_name_to_schema_property_id(csv_records_map)
        return json_data
```

Two methods to implement:
1. `_transform_csv_records_to_module_json_structure()` — Map sheet names to entity names
2. `_transform_csv_column_name_to_schema_property_id()` — Use `SchemaEngine.get_property_id()`

### Step 3: Create TransformJsonDataInteractor (if nested schema)

**File**: `bps/configio/{module}/interactors/transform_json_data_interactor.py`

Only needed if the schema has nested entities (parent-child relationships).

Implement:
- `to_nested(flat_data)` — Group children under parents
- `to_flat(nested_data)` — Extract children back to flat lists

### Step 4: Create DataStore

**File**: `bps/configio/{module}/data_store.py`

```python
class ModuleDataStore:
    def __init__(self, json_data, ...):
        self.json_data = json_data
        # Build lookup maps

    @property
    def entities(self):
        return self.json_data.get(JsonKeys.ENTITIES.value, [])

    def resolve_something(self, key):
        return self.lookup_map.get(key)
```

### Step 5: Create ImportStore (6 abstract methods)

**File**: `bps/configio/{module}/import_store.py`

```python
import bps.configio.{module}.action_generators  # noqa: F401
import bps.configio.{module}.run_actions_handlers  # noqa: F401

class ModuleImportStore(ImportStore):
    def __init__(self, ...):
        super().__init__(schema=MODULE_SCHEMA)
        self._csv_to_json_converter = ModuleCsvToJsonConverter()
        self._json_data_transformer = TransformJsonDataInteractor()

    def generate_action_entity_types(self): ...
    def convert_csv_to_json_data(self, csv_records_map): ...
    def convert_json_data_to_nested_data(self, flat_data): ...
    def convert_nested_data_to_flat_data(self, nested_data): ...
    def data_store(self, json_data): ...
    def get_existing_config(self, data_store): ...
```

### Step 6: Create Action Generators (one per entity type)

**File**: `bps/configio/{module}/action_generators/{entity}_action_generator.py`

For each entity type returned by `generate_action_entity_types()`:

1. Add enum value to `GenerateEntityActionEnum` if not already present
2. Create generator class extending `BulkEntityActionGenerator` or `SingularEntityActionGenerator`
3. Register with `@register_action_generator(entity_type)`
4. Implement `entity_type`, `entity_id_field`, `config_key`, `build_entity_dto()`
5. Import in `__init__.py`

### Step 7: Create RunActionHandlers (one per entity_type + action_type pair)

**File**: `bps/configio/{module}/run_actions_handlers/{entity}_{action}_action.py`

For each `(entity_type, action_type)` combination:

1. Create handler class extending `BaseConfigAction`
2. Register with `@register_bps_template_run_action(entity_type, action_type)`
3. Implement `entity_type`, `action_type`, `run_check()`, `execute()`
4. Add error codes to `RunActionErrorCodeEnum` if needed
5. Import in `__init__.py`

### Step 8: Create ImportInteractor (top-level entry point)

**File**: `bps/configio/{module}/import_interactor.py`

```python
class ImportModuleInteractor:
    def import_module(self, csv_path_map, ...):
        # Pre-processing (build lookup maps if needed)
        import_store = ModuleImportStore(...)
        interactor = ImportInteractor(import_store=import_store)
        return interactor.execute(
            csv_path_map=csv_path_map,
            sheet_filter_params_dtos=...,        # Optional
            csv_transformation_config_map=...,   # Optional
        )
```

### Step 9: Configure CSV Transformations (if needed)

**File**: `bps/configio/{module}/csvs_modifications.yaml`

Only if CSV data needs pre-processing (date format changes, string replacements, row filtering).

### Step 10: Test

1. Prepare sample CSV files matching the schema's `csv_column_name` values
2. Call the top-level import interactor
3. Verify entities are created/updated in the database
4. Test with existing data to verify UPDATE actions work correctly
5. Test validation errors produce readable `errors.csv`

---

## Common Patterns Across Modules

### Pattern: Import Calls Export

Every `get_existing_config()` calls the corresponding export interactor:

```python
# TDR Bank
def get_existing_config(self, data_store):
    interactor = ExportTdrBankInteractor()
    return interactor.export_tdr_bank(
        authority_wise_bank_id_map=data_store.get_authority_bank_map(),
        pipeline_item_ids=data_store.pipeline_item_ids,
    )

# Pipeline
def get_existing_config(self, data_store):
    interactor = ExportPipelineInteractor(...)
    return interactor.get_existing_nested_data(
        pipeline_item_template_id=data_store.pipeline_item_template_id
    )
```

### Pattern: Entity Type Order Matters

`generate_action_entity_types()` returns entities in dependency order — parents before children:

```python
# TDR Bank: Account -> Transaction -> TransactionLog -> Remarks
return [
    GenerateEntityActionEnum.TDR_ACCOUNT,
    GenerateEntityActionEnum.TDR_ACCOUNT_TRANSACTION,
    GenerateEntityActionEnum.TDR_ACCOUNT_TRANSACTION_LOG,
    GenerateEntityActionEnum.PIPELINE_ITEM_REMARKS,
]
```

### Pattern: Bulk vs Singular Generators

- Use `BulkEntityActionGenerator` for entities with multiple records (accounts, stages)
- Use `SingularEntityActionGenerator` for single-record entities (template config)

### Pattern: DataStore Registration

DataStores may need to register new IDs during CREATE action execution:

```python
# In DataStore
def register_account_id_for_account_no(self, account_no: str) -> str:
    account_id = generate_uuid4_str()
    self.account_no_wise_account_id_map[account_no] = account_id
    return account_id
```

This allows subsequent child entity handlers to look up the parent's newly assigned ID.
