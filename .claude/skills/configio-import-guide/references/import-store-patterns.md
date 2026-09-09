# ImportStore Patterns

## ImportStore ABC

**File**: `bps/configio/core/io_engine/import_store.py`

The core abstraction for import modules. Subclasses define how CSV data is converted, structured, stored, and compared.

```python
class ImportStore(abc.ABC):
    def __init__(self, schema: Dict):
        self.schema_obj = SchemaEngine(schema=schema)

    @abc.abstractmethod
    def generate_action_entity_types(self) -> List[GenerateEntityActionEnum]:
        """Returns the ordered list of entity types to generate actions for."""

    @abc.abstractmethod
    def convert_csv_to_json_data(self, csv_records_map: Dict[str, List[Any]]):
        pass

    @abc.abstractmethod
    def convert_json_data_to_nested_data(self, flat_data: Dict[str, Dict]):
        pass

    @abc.abstractmethod
    def convert_nested_data_to_flat_data(self, nested_data: Dict[str, Dict]):
        pass

    @abc.abstractmethod
    def data_store(self, json_data: Dict[str, Any]):
        pass

    @abc.abstractmethod
    def get_existing_config(self, data_store: Any) -> Dict[str, Any]:
        pass
```

### Concrete Method: `transform_to_json_data()`

Orchestrates the CSV-to-JSON pipeline:

```python
def transform_to_json_data(self, csv_records_map):
    # 1. Convert CSV column names -> JSON keys
    json_data = self.convert_csv_to_json_data(csv_records_map=csv_records_map)

    # 2. Validate foreign key references
    self._check_foreign_key_references(data=json_data, schema_obj=self.schema_obj)

    # 3. Group flat data into nested parent-child structure
    nested_data = self.convert_json_data_to_nested_data(flat_data=json_data)

    # 4. Schema validation
    validation_result = self.schema_obj.validate_data(data=nested_data)

    # 5. Type transformations (boolean, datetime, etc.)
    transformation_result = self.schema_obj.transform_data(data=nested_data)

    # 6. Flatten back for action generation
    json_data = self.convert_nested_data_to_flat_data(
        nested_data=transformation_result.transformed_data
    )

    return json_data, validation_result
```

---

## CsvToJsonConverter Pattern

**Each module creates its own converter.** The pattern is consistent:

### Two-Step Process

1. **Restructure by entity name** — Map CSV sheet identifiers to schema entity names
2. **Map column names to property IDs** — Use `SchemaEngine.get_property_id()`

### Example: TdrBankCsvToJsonConverter

**File**: `bps/configio/tdr_bank/json_converters/csv_json_to_converter.py`

```python
class TdrBankCsvToJsonConverter:
    def __init__(self):
        self._schema_engine = SchemaEngine(schema=TDR_BANK_SCHEMA)

    def convert(self, csv_records_map: Dict[str, List[Any]]) -> Dict[str, Any]:
        # Step 1: Restructure by entity name
        csv_records_map = self._transform_csv_records_to_tdr_bank_json_structure(
            csv_records_map=csv_records_map
        )
        # Step 2: Map column names to property IDs
        json_data = self._transform_csv_column_name_to_schema_property_id(
            csv_records_map=csv_records_map
        )
        return json_data
```

### Step 1: Restructure by Entity Name

Maps CSV file/sheet names to the schema's entity names:

```python
@staticmethod
def _transform_csv_records_to_tdr_bank_json_structure(csv_records_map):
    return {
        TDRBankJsonKeys.ACCOUNTS.value: csv_records_map.get(
            TDRBankJsonKeys.ACCOUNTS.value, []
        ),
        TDRBankJsonKeys.TRANSACTIONS.value: csv_records_map.get(
            TDRBankJsonKeys.TRANSACTIONS.value, []
        ),
        # ... more entities
    }
```

### Step 2: Map Column Names to Property IDs

Iterates each record in each entity and resolves CSV column names to JSON property IDs:

```python
def _convert_csv_to_json(self, entity_name, records):
    json_data_list = []
    undefined_columns = set()

    for record_dict in records:
        json_data = {}
        for key, value in record_dict.items():
            property_id = self._schema_engine.get_property_id(
                entity_name=entity_name, csv_column_name=key
            )
            if property_id is None:
                undefined_columns.add(key)
                continue
            json_data[property_id] = value or None
        json_data_list.append(json_data)

    return json_data_list, undefined_columns
```

Raises `PropertiesNotFoundForCSVColumns` if any CSV columns cannot be mapped to schema properties.

---

## Flat-to-Nested Conversion

Groups flat entity records into parent-child hierarchies for schema validation.

### Example: TDR Bank Nesting

**File**: `bps/configio/tdr_bank/interactors/transform_tdr_bank_json_data.py`

Flat structure:
```json
{
    "tdr_certificates": [...],
    "transactions": [...],
    "transaction_logs": [...]
}
```

Nested structure (for schema validation):
```json
{
    "tdr_certificates": [
        {
            "tdr_certificate_no": "...",
            "transactions": [
                {
                    "transaction_id": "...",
                    "transaction_logs": [...]
                }
            ]
        }
    ]
}
```

The `to_nested()` method:
1. Applies domain-specific transformations (e.g., `_update_transaction_statuses()`, `_update_creation_ref_type_in_accounts()`)
2. Groups transaction logs by `transaction_id`
3. Attaches transaction logs to their parent transactions
4. Groups transactions by `tdr_certificate_no`
5. Attaches transactions to their parent accounts

**Note**: `to_nested()` can accept extra parameters for domain-specific logic. The TDR Bank version takes `application_id_to_pipeline_item_id_map` to determine creation reference types. Pipeline's version takes no extra parameters.

```python
def to_nested(self, flat_data, application_id_to_pipeline_item_id_map):
    accounts = flat_data.get(TDRBankJsonKeys.ACCOUNTS.value, [])
    transactions = flat_data.get(TDRBankJsonKeys.TRANSACTIONS.value, [])
    transaction_logs = flat_data.get(TDRBankJsonKeys.TRANSACTION_LOGS.value, [])

    # Group and attach: logs -> transactions -> accounts
    transaction_wise_logs = self._group_transaction_logs_by_transaction(transaction_logs)
    transactions_with_logs = self._attach_transaction_logs_to_transactions(
        transactions, transaction_wise_logs
    )
    account_wise_transactions = self._group_transactions_by_account(transactions_with_logs)
    accounts_with_transactions = self._attach_transactions_to_accounts(
        accounts, account_wise_transactions
    )
    return {TDRBankJsonKeys.ACCOUNTS.value: accounts_with_transactions, ...}
```

### Nested-to-Flat Reconversion

The `to_flat()` method reverses the nesting after schema validation:

```python
def to_flat(self, nested_data):
    accounts = nested_data.get(TDRBankJsonKeys.ACCOUNTS.value, [])
    transactions = self._extract_transactions_from_accounts(accounts)
    transaction_logs = self._extract_transaction_logs_from_transactions(transactions)
    note_sheets = nested_data.get(TDRBankJsonKeys.NOTE_SHEETS.value, [])
    return {
        TDRBankJsonKeys.ACCOUNTS.value: accounts,
        TDRBankJsonKeys.TRANSACTIONS.value: transactions,
        TDRBankJsonKeys.TRANSACTION_LOGS.value: transaction_logs,
        TDRBankJsonKeys.NOTE_SHEETS.value: note_sheets,
    }
```

---

## Schema Validation

### Validation Flow

```python
# In transform_to_json_data():
validation_result = self.schema_obj.validate_data(data=nested_data)
transformation_result = self.schema_obj.transform_data(data=nested_data)
```

- `validate_data()` checks types, required fields, unique constraints, enums
- `transform_data()` applies type transformations (e.g., string "true" -> boolean True)
- Foreign key validation is done separately via `_check_foreign_key_references()`

### Foreign Key Validation

```python
@staticmethod
def _check_foreign_key_references(data, schema_obj):
    foreign_key_errors = schema_obj.validate_foreign_keys(data=data)
    if foreign_key_errors:
        error_messages = "\n".join(
            [error.error_message for error in foreign_key_errors]
        )
        raise ValidationError(f"Foreign key errors: {error_messages}")
```

---

## DataStore Pattern

An in-memory lookup object that provides resolution methods used during action generation and execution.

### Example: TdrBankDataStore

**File**: `bps/configio/tdr_bank/data_store.py`

```python
class TdrBankDataStore:
    def __init__(self, json_data, authority_wise_bank_id_map,
                 account_no_wise_account_id_map, ...):
        self.json_data = json_data
        self.authority_wise_bank_id_map = authority_wise_bank_id_map
        self.account_no_wise_account_id_map = account_no_wise_account_id_map
        # Build lookup maps
        self.transaction_id_to_transaction_map = {
            t.get(TransactionJsonKeys.TRANSACTION_ID.value): t
            for t in self.transactions
        }

    @property
    def accounts(self) -> List[Dict[str, Any]]:
        return self.json_data.get(TDRBankJsonKeys.ACCOUNTS.value, [])

    def get_bank_id_for_authority(self, authority: str) -> str:
        return self.authority_wise_bank_id_map[authority]

    def get_account_id_by_account_no(self, account_no: str) -> Optional[str]:
        return self.account_no_wise_account_id_map.get(account_no)

    def register_account_id_for_account_no(self, account_no: str) -> str:
        account_id = generate_uuid4_str()
        self.account_no_wise_account_id_map[account_no] = account_id
        return account_id
```

### DataStore Design Guidelines

1. Accept `json_data` and any pre-fetched lookup maps in `__init__`
2. Provide `@property` accessors for entity lists from `json_data`
3. Implement lookup methods used by action generators and handlers
4. Support mutable state for registration during action execution (e.g., `register_account_id_for_account_no`)

### Example: BPSPipelinesDataStore (Simple)

**File**: `bps/configio/pipeline/data_store.py`

```python
class BPSPipelinesDataStore:
    def __init__(self, json_data, pipeline_item_template_id):
        self.pipeline_item_template_id = pipeline_item_template_id
        self.json_data = json_data
        # Fetch field mappings from service
        self.reference_id_field_mapping = {
            field.reference_id: field.field_id for field in fields
        }

    @property
    def pipelines(self) -> List[Dict[str, Any]]:
        return self.json_data.get(PipelineConfigJsonKeys.PIPELINES.value, [])

    def get_field_id_from_reference_id(self, field_ref_id):
        return self.reference_id_field_mapping.get(field_ref_id, field_ref_id)
```

---

## Concrete ImportStore Examples

### TdrBankImportStore

**File**: `bps/configio/tdr_bank/import_store.py`

```python
class TdrBankImportStore(ImportStore):
    def __init__(self, authority_wise_bank_id_map, account_no_wise_account_id_map, ...):
        super().__init__(schema=TDR_BANK_SCHEMA)
        self.authority_wise_bank_id_map = authority_wise_bank_id_map
        self._csv_to_json_converter = TdrBankCsvToJsonConverter()
        self._json_data_transformer = TransformTdrBankJsonDataInteractor()

    def generate_action_entity_types(self):
        return [
            GenerateEntityActionEnum.TDR_ACCOUNT,
            GenerateEntityActionEnum.TDR_ACCOUNT_TRANSACTION,
            GenerateEntityActionEnum.TDR_ACCOUNT_TRANSACTION_LOG,
            GenerateEntityActionEnum.PIPELINE_ITEM_REMARKS,
        ]

    def convert_csv_to_json_data(self, csv_records_map):
        return self._csv_to_json_converter.convert(csv_records_map=csv_records_map)

    def convert_json_data_to_nested_data(self, flat_data):
        return self._json_data_transformer.to_nested(flat_data=flat_data, ...)

    def convert_nested_data_to_flat_data(self, nested_data):
        return self._json_data_transformer.to_flat(nested_data=nested_data)

    def data_store(self, json_data):
        return TdrBankDataStore(json_data=json_data, ...)

    def get_existing_config(self, data_store):
        interactor = ExportTdrBankInteractor()
        return interactor.export_tdr_bank(
            authority_wise_bank_id_map=data_store.get_authority_bank_map(),
            pipeline_item_ids=data_store.pipeline_item_ids,
        )
```

### PipelineImportStore

**File**: `bps/configio/pipeline/import_store.py`

```python
class PipelineImportStore(ImportStore):
    def __init__(self, pipeline_item_template_id):
        super().__init__(schema=BPS_PIPELINES_SCHEMA)
        self.pipeline_item_template_id = pipeline_item_template_id
        self._csv_to_json_converter = PipelineCsvToJsonConverter()
        self._json_data_transformer = TransformPipelineJsonDataInteractor()

    def generate_action_entity_types(self):
        return [
            GenerateEntityActionEnum.PIPELINE,
            GenerateEntityActionEnum.CONDITIONAL_ACTION_RULE,
            GenerateEntityActionEnum.APPLICATION_ID_GENERATION_CONFIG,
            # ... more entity types
            GenerateEntityActionEnum.STAGE_TRANSITION,
        ]

    def get_existing_config(self, data_store):
        interactor = ExportPipelineInteractor(...)
        return interactor.get_existing_nested_data(
            pipeline_item_template_id=data_store.pipeline_item_template_id
        )
```

**Key difference**: `PipelineImportStore` is simpler — fewer pre-fetched maps, simpler DataStore.

---

## ImportStore Registration Pattern

ImportStore subclasses must import their action generators and run action handlers in the module to trigger decorator registration:

```python
# At the top of import_store.py
import bps.configio.tdr_bank.action_generators  # noqa: F401
import bps.configio.tdr_bank.run_actions_handlers  # noqa: F401
```

Without these imports, the `@register_action_generator` and `@register_bps_template_run_action` decorators never execute, and the registries remain empty.
