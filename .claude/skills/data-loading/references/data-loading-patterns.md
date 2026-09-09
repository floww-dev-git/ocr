# Data Loading Patterns Reference

## Entry Point — InitiateDataLoadingRequestFromCSV

The existing mutation at `sales_crm_graphql.data_loading_requests.mutations.csv.initiate_data_loading_request_from_csv` provides:
- File upload handling
- CSV parsing
- Row-by-row processing dispatch
- Error aggregation and reporting

New data loading features integrate into this mutation by adding a new entity type handler.

## Populate Interactor Pattern

From `sales_crm_core.populate.populate_layout_tabs.populate_layout_tabs.PopulateTabsInteractor`:

```python
class PopulateTabsInteractor:
    def __init__(self, storage: TabStorageInterface):
        self.storage = storage

    def populate_tabs(self, rows: List[TabRowDTO]) -> PopulateResultDTO:
        errors = []
        created_count = 0

        for row in rows:
            try:
                self._validate_row(row)
                self._process_row(row)
                created_count += 1
            except ValidationError as e:
                errors.append(RowErrorDTO(
                    row_number=row.row_number,
                    error=str(e),
                ))

        return PopulateResultDTO(
            created_count=created_count,
            error_count=len(errors),
            errors=errors,
        )
```

**Key patterns:**
- Error collection (don't fail on first error)
- Row-by-row processing with try/except per row
- Return summary DTO with counts and error details

## Update or Create Pattern

From `UpdateOrCreateTabFromDataLoadingInteractor`:

```python
class UpdateOrCreateTabFromDataLoadingInteractor:
    def process_row(self, row_dto: TabRowDTO):
        existing = self.storage.get_tab_by_unique_key(
            pipeline_id=row_dto.pipeline_id,
            name=row_dto.name,
        )

        if existing:
            self._update_existing(existing, row_dto)
        else:
            self._create_new(row_dto)
```

**Key patterns:**
- Check for existing entity before create
- Separate update and create logic
- Use unique key combination for lookup

## CSV Row DTO Pattern

```python
@dataclass
class CsvRowDTO:
    row_number: int
    # Data fields matching CSV columns
    entity_name: str
    entity_type: str
    parent_id: str
    config_json: str  # Raw JSON string from CSV

@dataclass
class RowErrorDTO:
    row_number: int
    error: str

@dataclass
class DataLoadingResultDTO:
    total_rows: int
    created_count: int
    updated_count: int
    error_count: int
    errors: List[RowErrorDTO]
```

## Validation Pattern

```python
class DataLoadingValidator:
    def validate_row(self, row: CsvRowDTO) -> List[str]:
        errors = []

        # Required field checks
        if not row.entity_name:
            errors.append("entity_name is required")

        # Enum validation
        if row.entity_type not in EntityType.get_list_of_values():
            errors.append(f"Invalid entity_type: {row.entity_type}")

        # JSON validation
        if row.config_json:
            try:
                config = json.loads(row.config_json)
                self._validate_config_schema(config)
            except json.JSONDecodeError:
                errors.append("config_json is not valid JSON")

        # Relationship validation
        if row.parent_id:
            valid_ids = self.storage.get_valid_entity_ids([row.parent_id])
            if not valid_ids:
                errors.append(f"Parent entity not found: {row.parent_id}")

        return errors
```

## Integration with Existing Mutation

New data loading features integrate by:
1. Adding a new entity type constant
2. Creating a handler interactor for that entity type
3. Registering the handler in the mutation's dispatch logic
4. Following the same error collection and reporting pattern
