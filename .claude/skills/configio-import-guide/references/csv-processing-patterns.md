# CSV Processing Patterns

## CSVReader

**File**: `bps/configio/core/csv_utils/csv_reader.py`

Reads a CSV file into a list of dictionaries, one per row. Strips whitespace from both keys and values.

```python
class CSVReader:
    def read_csv(self, file_path: str) -> List[Dict[str, Any]]:
        self._validate_file_exists(file_path=file_path)
        return self._parse_csv_file(file_path=file_path)
```

- Uses `csv.DictReader` for parsing
- Raises `CsvFileNotFoundError` if file does not exist
- Raises `CsvParseError` on CSV parsing or encoding errors
- Returns `List[Dict[str, Any]]` where each dict maps column name -> value

---

## CSV Filtering

**File**: `bps/configio/core/io_engine/import_store.py` (static methods on `ImportStore`)

Filtering uses a two-level DTO hierarchy:

### DTO Hierarchy

```
SheetFilterParamsDTO
|-- sheet_name: str                     # CSV file/sheet identifier
|-- filter_params_dto: FilterParamsDTO
    |-- filters: List[CSVRowFilterDTO]           # Include rows matching any filter
    |-- include_column_names: Optional[List[str]] # Keep only these columns
    |-- column_overrides: Optional[List[ColumnOverrideDTO]]  # Set fixed values
    |-- string_replacements: Optional[List[StringReplacementDTO]]  # Find/replace
    |-- primary_key: Optional[str]               # Exclude rows with empty primary key
    |-- exclude_rows: Optional[List[ExcludeRowDTO]]  # Exclude rows matching values
```

### Filter DTOs (from `bps/configio/core/io_engine/dtos.py`)

```python
@dataclass
class CSVRowFilterDTO:
    column_name: str
    value: str

@dataclass
class ColumnOverrideDTO:
    column_name: str
    value: str

@dataclass
class StringReplacementDTO:
    column_name: str
    find_string: str
    replace_string: str

@dataclass
class ExcludeRowDTO:
    column_name: str
    values: List[str]

@dataclass
class FilterParamsDTO:
    filters: List[CSVRowFilterDTO]
    include_column_names: Optional[List[str]] = None
    column_overrides: Optional[List[ColumnOverrideDTO]] = None
    string_replacements: Optional[List[StringReplacementDTO]] = None
    primary_key: Optional[str] = None
    exclude_rows: Optional[List[ExcludeRowDTO]] = None

@dataclass
class SheetFilterParamsDTO:
    sheet_name: str
    filter_params_dto: FilterParamsDTO
```

### Filter Flow (per row)

```
1. Exclude rows   - If row matches any ExcludeRowDTO -> skip row
2. Include rows   - If filters exist, row must match at least one CSVRowFilterDTO
3. Primary key    - If primary_key set, row must have non-empty value for that column
4. Filter columns - Keep only columns in include_column_names (if set)
5. Apply overrides- Override specific column values with fixed values
6. Apply replacements - Find/replace strings in specific columns
```

All string comparisons are case-insensitive (`.upper()` comparison).

---

## CSVTransformer

**File**: `bps/configio/core/csv_utils/csv_transformer.py`

A more powerful transformation engine driven by `CSVTransformationConfigDTO`.

```python
class CSVTransformer:
    def process(
        self,
        records: List[Dict[str, Any]],
        config: CSVTransformationConfigDTO,
    ) -> CSVProcessingResultDTO:
```

### CSVTransformationConfigDTO (from `bps/configio/core/csv_utils/dtos/transformation_dtos.py`)

```python
@dataclass
class CSVTransformationConfigDTO:
    include_row_filters: Optional[List[RowFilterConfigDTO]] = None
    exclude_row_filters: Optional[List[RowFilterConfigDTO]] = None
    include_columns: Optional[ColumnFilterConfigDTO] = None
    value_transformations: Optional[List[ValueTransformationConfigDTO]] = None
    column_overrides: Optional[List[ColumnOverrideConfigDTO]] = None
```

### Processing Pipeline (per row)

```
1. Row filtering   - Include/exclude rows based on RowFilterConfigDTO
2. Column filtering - Keep only columns in ColumnFilterConfigDTO.column_names
3. Value transforms - Apply registered transformers (string pattern, datetime, etc.)
4. Column overrides - Set fixed values for specific columns
```

### Value Transformer Types

| Type | DTO | Purpose |
|------|-----|---------|
| `STRING_PATTERN_REPLACE` | `StringPatternReplaceConfigDTO` | Regex find/replace |
| `EXACT_REPLACE` | `ExactReplaceConfigDTO` | Exact string replacement |
| `DATETIME_FORMAT` | `DatetimeFormatConfigDTO` | Convert datetime formats |

Transformers are registered via decorator pattern in `TransformerRegistry`.

### Result DTO

```python
@dataclass
class CSVProcessingResultDTO:
    processed_records: List[Dict[str, Any]]
    total_input_records: int
    total_output_records: int
    filtered_out_count: int
```

---

## YAML Configuration

**File**: `bps/configio/core/csv_utils/csv_transformation_config_factory.py`

```python
class CSVTransformationConfigFactory:
    @classmethod
    def from_yaml_file(
        cls, file_path: str,
    ) -> Dict[str, CSVTransformationConfigDTO]:
```

### YAML Structure

```yaml
csv_configs:
  sheet_name_1:
    include_row_filters:
      - column_name: "Status"
        value: "Active"
        case_sensitive: false
    exclude_row_filters:
      - column_name: "Type"
        value: "Draft"
    include_columns:
      column_names:
        - "Column A"
        - "Column B"
    value_transformations:
      - column_name: "Date"
        transformation_type: "DATETIME_FORMAT"
        from_format: "%d/%m/%Y"
        to_format: "%Y-%m-%d"
      - column_name: "Name"
        transformation_type: "STRING_PATTERN_REPLACE"
        find_pattern: "\\s+"
        replace_with: " "
    column_overrides:
      - column_name: "Source"
        value: "CSV Import"
  sheet_name_2:
    # ... same structure
```

### Usage in Import Interactor

```python
def _get_csv_transformation_config_map(self) -> Dict[str, CSVTransformationConfigDTO]:
    return CSVTransformationConfigFactory.from_yaml_file(
        file_path="bps/configio/tdr_bank/csvs_modifications.yaml"
    )
```

The returned map is keyed by CSV sheet name and passed to `ImportInteractor.execute()` as `csv_transformation_config_map`.

---

## How Filtering Fits in the Import Pipeline

```
ImportInteractor.execute()
|-- _parse_csv_files()                # CSVReader per file
|-- ImportStore.filter_csv_records()  # SheetFilterParamsDTO-based filtering
|-- _apply_csv_transformations()      # CSVTransformer with YAML config
|-- ImportStore.transform_to_json_data()  # CSV -> JSON conversion
```

Both filtering mechanisms (`filter_csv_records` and `_apply_csv_transformations`) operate on the raw CSV records **before** CSV-to-JSON conversion.
