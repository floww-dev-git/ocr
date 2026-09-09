# Schema Definition Patterns

Comprehensive guide for defining configio schemas used by the SchemaEngine for export and validation.

## Schema Structure Overview

```python
MY_MODULE_SCHEMA = {
    "entity_name": {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "property_id": {
                    "type": "string",
                    "csv_column_name": "CSV Header Name",
                    # Optional constraints...
                }
            }
        }
    }
}
```

## Property Types

### Basic Types

```python
# String
"name": {
    "type": "string",
    "csv_column_name": "Name",
    "required": True,
    "min_length": 1,
    "max_length": 255,
}

# Integer
"order": {
    "type": "integer",
    "csv_column_name": "Order",
    "min_value": 1,
}

# Boolean (transforms to YES/NO in CSV)
"is_active": {
    "type": "boolean",
    "csv_column_name": "Is Active",
}

# Float/Decimal
"amount": {
    "type": "float",
    "csv_column_name": "Amount",
}
```

### Foreign Key Type

```python
"pipeline_name": {
    "type": "foreign_key",
    "csv_column_name": "Pipeline Name",
    "foreign_key_reference": "pipelines.name",      # Target entity.property
    "foreign_key_path": "stages.pipeline_name",     # Source path
    "required": True,
}

# Multiple references
"stage_id": {
    "type": "foreign_key",
    "csv_column_name": "Stage ID",
    "foreign_key_references": ["stages.stage_id", "display_stages.stage_id"],
}
```

### Condition Type (for rule engines)

```python
# Dynamic condition columns
CONDITIONS_PROPERTIES = {
    f"condition_{i}": {
        "type": "condition",
        "csv_column_name": f"Condition {i}",
    }
    for i in range(1, MAX_CONDITIONS + 1)
}
```

## Property Constraints

```python
"property_id": {
    "type": "string",
    "csv_column_name": "Property Name",

    # Validation constraints
    "required": True,                              # Must have value
    "unique": True,                                # Must be unique across records
    "min_length": 1,                               # Minimum string length
    "max_length": 255,                             # Maximum string length
    "min_value": 0,                                # Minimum numeric value
    "pattern": r"^[A-Z]{2}\d{4}$",                # Regex pattern
    "allowed_values": ["VALUE_1", "VALUE_2"],     # Enum values

    # Key constraints
    "primary_key": True,                           # Entity primary key
}
```

## Nested Entity Schemas

### Child Entities in Parent

```python
STAGES = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            # Nested child entities
            "stage_fee_rule_sets": STAGE_FEE_RULE_SETS,
            "add_another_gof_permissions": ADD_ANOTHER_GOF_PERMISSIONS,

            # Stage properties
            "stage_id": {
                "type": "string",
                "csv_column_name": "Stage ID",
                "unique": True,
                "required": True,
            },
            "pipeline_name": {
                "type": "foreign_key",
                "csv_column_name": "Pipeline Name",
                "foreign_key_reference": "pipelines.name",
            },
            # ... more properties
        }
    }
}
```

### Flat Schema with Relationships

```python
# For export, use flat schema with foreign keys
BPS_PIPELINES_SCHEMA = {
    "pipelines": PIPELINES,
    "stages": STAGES,                                    # Flat entity
    "conditional_action_rules": CONDITIONAL_ACTION_RULES,
    "stage_transitions": STAGE_TRANSITIONS,
}
```

## Complete Schema Example (TDR Bank)

```python
# From bps/configio/tdr_bank/schema.py

TDR_CERTIFICATES = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            AccountJsonKeys.TDR_CERTIFICATE_NO.value: {
                "type": "string",
                "csv_column_name": "TDR Certificate No.",
                "unique": True,
                "required": True,
            },
            AccountJsonKeys.AUTHORITY.value: {
                "type": "string",
                "csv_column_name": "Authority",
                "required": True,
            },
            AccountJsonKeys.PHONE_NUMBER.value: {
                "type": "string",
                "csv_column_name": "Phone Number",
            },
            AccountJsonKeys.TOTAL_AREA_IN_SQ_YARDS.value: {
                "type": "float",
                "csv_column_name": "Total Area in Sq. Yards",
            },
            AccountJsonKeys.TDR_APPLICATION_ID.value: {
                "type": "string",
                "csv_column_name": "TDR Application Id",
            },
            AccountJsonKeys.CREATION_TYPE.value: {
                "type": "string",
                "csv_column_name": "Creation Type",
                "allowed_values": CreationType.get_list_of_values(),
            },
            AccountJsonKeys.ISSUED_DATE_TIME.value: {
                "type": "string",
                "csv_column_name": "Issued Date Time",
            },
            AccountJsonKeys.PARENT_TDR_CERTIFICATE_NO.value: {
                "type": "foreign_key",
                "csv_column_name": "Parent TDR Certificate No.",
                "foreign_key_reference": "tdr_certificates.tdr_certificate_no",
            },
            AccountJsonKeys.CERTIFICATE_LINK.value: {
                "type": "string",
                "csv_column_name": "Certificate Link",
            },
        }
    }
}

TRANSACTIONS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            TransactionJsonKeys.TRANSACTION_ID.value: {
                "type": "string",
                "csv_column_name": "Transaction ID",
                "unique": True,
                "required": True,
            },
            TransactionJsonKeys.TDR_CERTIFICATE_NO.value: {
                "type": "foreign_key",
                "csv_column_name": "TDR Certificate No.",
                "foreign_key_reference": "tdr_certificates.tdr_certificate_no",
                "required": True,
            },
            TransactionJsonKeys.STATUS.value: {
                "type": "string",
                "csv_column_name": "Status",
                "allowed_values": TransactionStatus.get_list_of_values(),
            },
            TransactionJsonKeys.AREA_REQUESTED.value: {
                "type": "float",
                "csv_column_name": "Area in Sq. Yards Requested",
            },
            TransactionJsonKeys.CREATION_DATETIME.value: {
                "type": "string",
                "csv_column_name": "Creation Date Time",
            },
        }
    }
}

# Complete schema
TDR_BANK_SCHEMA = {
    TDRBankJsonKeys.ACCOUNTS.value: TDR_CERTIFICATES,       # "tdr_certificates"
    TDRBankJsonKeys.TRANSACTIONS.value: TRANSACTIONS,       # "transactions"
    TDRBankJsonKeys.TRANSACTION_LOGS.value: TRANSACTION_LOGS,
    TDRBankJsonKeys.NOTE_SHEETS.value: NOTE_SHEETS,
}
```

## Using JSON Key Enums

Always define JSON keys as enums for consistency:

```python
# constants/json_keys.py
class TDRBankJsonKeys(BaseEnumClass, enum.Enum):
    ACCOUNTS = "tdr_certificates"
    TRANSACTIONS = "transactions"
    TRANSACTION_LOGS = "transaction_change_logs"

class AccountJsonKeys(BaseEnumClass, enum.Enum):
    TDR_CERTIFICATE_NO = "tdr_certificate_no"
    AUTHORITY = "authority"
    PHONE_NUMBER = "phone_number"
    TOTAL_AREA_IN_SQ_YARDS = "total_area_in_sq_yards"
```

## SchemaEngine Usage

```python
from bps.configio.core.schema_engine import SchemaEngine

class MyExportCSVInteractor:
    def __init__(self):
        self.schema = SchemaEngine(MY_MODULE_SCHEMA)

    def get_csv_column_names(self, entity_name: str) -> List[str]:
        return self.schema.get_csv_column_names_for_entity(entity_name)

    def transform_to_csv(self, json_data: Dict) -> Dict:
        return self.schema.transform_flat_data_to_csv(json_data)
```

## Key Files Reference

| Component | File Path |
|-----------|-----------|
| SchemaEngine | `bps/configio/core/schema_engine/schema_engine.py` |
| Schema Constants | `bps/configio/core/schema_engine/constants.py` |
| TDR Bank Schema | `bps/configio/tdr_bank/schema.py` |
| Pipeline Schema (Complex) | `bps/configio/pipeline/schema.py` |
| TDR JSON Keys | `bps/configio/tdr_bank/constants/json_keys.py` |
