# Complete Configio Export Examples

Full implementation examples for reference when creating new configio export modules.

## Example 1: TDR Bank Export (Simple - 4 Entities)

### Directory Structure
```
bps/configio/tdr_bank/
├── __init__.py
├── schema.py
├── export_interactor.py
├── export_csv_interactor.py
├── dtos.py
└── constants/
    ├── __init__.py
    └── json_keys.py
```

### 1. JSON Keys (`constants/json_keys.py`)

```python
import enum
from common.utils.base_enum_class import BaseEnumClass


class TDRBankJsonKeys(BaseEnumClass, enum.Enum):
    """Top-level entity names."""
    ACCOUNTS = "tdr_certificates"
    TRANSACTIONS = "transactions"
    TRANSACTION_LOGS = "transaction_change_logs"
    NOTE_SHEETS = "note_sheets"


class AccountJsonKeys(BaseEnumClass, enum.Enum):
    """Account entity properties."""
    TDR_CERTIFICATE_NO = "tdr_certificate_no"
    AUTHORITY = "authority"
    PHONE_NUMBER = "phone_number"
    TOTAL_AREA_IN_SQ_YARDS = "total_area_in_sq_yards"
    TDR_APPLICATION_ID = "application_id"
    CREATION_TYPE = "creation_type"
    ISSUED_DATE_TIME = "issued_date_time"
    PARENT_TDR_CERTIFICATE_NO = "parent_tdr_certificate_no"
    CERTIFICATE_LINK = "certificate_link"
    LOI_LINK = "letter_of_intent_loi_link"
    SHORTFALL_LETTER_LINK = "shortfall_letter_link"


class TransactionJsonKeys(BaseEnumClass, enum.Enum):
    """Transaction entity properties."""
    TRANSACTION_ID = "transaction_id"
    TDR_CERTIFICATE_NO = "tdr_certificate_no"
    TRANSACTION_OPERATION = "transaction_operation"
    STATUS = "status"
    AREA_REQUESTED = "area_in_sq_yards_requested"
    ISSUED_AREA = "issued_area"
    BALANCE = "balance"
    FILE_NO = "file_no"
    APPLICANT_NAME = "applicant_name"
    MARKET_VALUE = "market_value_of_usage_area"
    CREATION_DATETIME = "creation_datetime"
    LAST_UPDATE_DATETIME = "last_update_datetime"
    ACTED_BY = "acted_by"


class TransactionLogJsonKeys(BaseEnumClass, enum.Enum):
    """Transaction log entity properties."""
    LOG_ID = "log_id"
    TRANSACTION_ID = "transaction_id"
    STATUS = "status"
    ACTED_BY = "acted_by"
    DATETIME = "datetime"
```

### 2. Schema Definition (`schema.py`)

```python
from bps.configio.tdr_bank.constants.json_keys import (
    AccountJsonKeys,
    TDRBankJsonKeys,
    TransactionJsonKeys,
    TransactionLogJsonKeys,
)

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
            AccountJsonKeys.LOI_LINK.value: {
                "type": "string",
                "csv_column_name": "LOI Link",
            },
            AccountJsonKeys.SHORTFALL_LETTER_LINK.value: {
                "type": "string",
                "csv_column_name": "Shortfall Letter Link",
            },
        },
    },
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
            TransactionJsonKeys.TRANSACTION_OPERATION.value: {
                "type": "string",
                "csv_column_name": "Transaction Operation",
            },
            TransactionJsonKeys.STATUS.value: {
                "type": "string",
                "csv_column_name": "Status",
            },
            TransactionJsonKeys.AREA_REQUESTED.value: {
                "type": "float",
                "csv_column_name": "Area in Sq. Yards Requested",
            },
            TransactionJsonKeys.ISSUED_AREA.value: {
                "type": "float",
                "csv_column_name": "Issued Area",
            },
            TransactionJsonKeys.BALANCE.value: {
                "type": "float",
                "csv_column_name": "Balance",
            },
            TransactionJsonKeys.FILE_NO.value: {
                "type": "string",
                "csv_column_name": "File No.",
            },
            TransactionJsonKeys.APPLICANT_NAME.value: {
                "type": "string",
                "csv_column_name": "Applicant Name",
            },
            TransactionJsonKeys.CREATION_DATETIME.value: {
                "type": "string",
                "csv_column_name": "Creation Date Time",
            },
            TransactionJsonKeys.LAST_UPDATE_DATETIME.value: {
                "type": "string",
                "csv_column_name": "Last Update Date Time",
            },
            TransactionJsonKeys.ACTED_BY.value: {
                "type": "string",
                "csv_column_name": "Acted By",
            },
        },
    },
}

TRANSACTION_LOGS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            TransactionLogJsonKeys.LOG_ID.value: {
                "type": "string",
                "csv_column_name": "Log ID",
                "unique": True,
                "required": True,
            },
            TransactionLogJsonKeys.TRANSACTION_ID.value: {
                "type": "foreign_key",
                "csv_column_name": "Transaction ID",
                "foreign_key_reference": "transactions.transaction_id",
                "required": True,
            },
            TransactionLogJsonKeys.STATUS.value: {
                "type": "string",
                "csv_column_name": "Status",
            },
            TransactionLogJsonKeys.ACTED_BY.value: {
                "type": "string",
                "csv_column_name": "Acted By",
            },
            TransactionLogJsonKeys.DATETIME.value: {
                "type": "string",
                "csv_column_name": "Date Time",
            },
        },
    },
}

NOTE_SHEETS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "note_sheet_id": {
                "type": "string",
                "csv_column_name": "Note Sheet ID",
                "unique": True,
                "required": True,
            },
            "pipeline_item_id": {
                "type": "string",
                "csv_column_name": "Pipeline Item ID",
                "required": True,
            },
            "content": {
                "type": "string",
                "csv_column_name": "Content",
            },
            "created_at": {
                "type": "string",
                "csv_column_name": "Created At",
            },
        },
    },
}

# Complete schema
TDR_BANK_SCHEMA = {
    TDRBankJsonKeys.ACCOUNTS.value: TDR_CERTIFICATES,
    TDRBankJsonKeys.TRANSACTIONS.value: TRANSACTIONS,
    TDRBankJsonKeys.TRANSACTION_LOGS.value: TRANSACTION_LOGS,
    TDRBankJsonKeys.NOTE_SHEETS.value: NOTE_SHEETS,
}
```

### 3. Export Interactor (`export_interactor.py`)

```python
from typing import Any, Dict, List, Tuple

from bps.adapters.service_adapter import get_service_adapter
from bps.configio.tdr_bank.constants.json_keys import TDRBankJsonKeys


class ExportTdrBankInteractor:
    @property
    def tdr_service(self):
        return get_service_adapter().tdr

    @property
    def sales_crm_service(self):
        return get_service_adapter().sales_crm_service

    def export_tdr_bank(
        self,
        authority_wise_bank_id_map: Dict[str, str],
        pipeline_item_ids: List[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        # 1. Gather root entities (accounts)
        accounts_json, account_ids = self._get_accounts_json(
            authority_wise_bank_id_map=authority_wise_bank_id_map
        )

        # 2. Gather child entities (transactions)
        transactions_json, transaction_ids = self._get_transactions_json(
            account_ids=account_ids
        )

        # 3. Gather grandchild entities (transaction logs)
        transaction_logs_json = self._get_transaction_logs_json(
            transaction_ids=transaction_ids
        )

        # 4. Gather related entities (note sheets)
        note_sheets_json = self._get_note_sheets_json(
            pipeline_item_ids=pipeline_item_ids
        )

        return {
            TDRBankJsonKeys.ACCOUNTS.value: list(accounts_json.values()),
            TDRBankJsonKeys.TRANSACTIONS.value: list(transactions_json.values()),
            TDRBankJsonKeys.TRANSACTION_LOGS.value: list(transaction_logs_json.values()),
            TDRBankJsonKeys.NOTE_SHEETS.value: list(note_sheets_json.values()),
        }

    def _get_accounts_json(
        self, authority_wise_bank_id_map: Dict[str, str]
    ) -> Tuple[Dict[str, Dict], List[str]]:
        bank_ids = list(authority_wise_bank_id_map.values())

        accounts_json = self.tdr_service.get_accounts_json(
            bank_ids=bank_ids,
            authority_wise_bank_id_map=authority_wise_bank_id_map,
        )

        account_ids = list(accounts_json.keys())
        return accounts_json, account_ids

    def _get_transactions_json(
        self, account_ids: List[str]
    ) -> Tuple[Dict[str, Dict], List[str]]:
        if not account_ids:
            return {}, []

        transactions_json = self.tdr_service.get_transactions_json_for_accounts(
            account_ids=account_ids
        )

        transaction_ids = list(transactions_json.keys())
        return transactions_json, transaction_ids

    def _get_transaction_logs_json(
        self, transaction_ids: List[str]
    ) -> Dict[str, Dict]:
        if not transaction_ids:
            return {}

        return self.tdr_service.get_transaction_logs_json_for_transactions(
            transaction_ids=transaction_ids
        )

    def _get_note_sheets_json(
        self, pipeline_item_ids: List[str]
    ) -> Dict[str, Dict]:
        if not pipeline_item_ids:
            return {}

        return self.sales_crm_service.get_note_sheets_json(
            pipeline_item_ids=pipeline_item_ids
        )
```

### 4. CSV Export Interactor (`export_csv_interactor.py`)

```python
from typing import Any, Dict, List

from bps.configio.core.csv_utils import CSVWriter
from bps.configio.core.schema_engine import SchemaEngine
from bps.configio.tdr_bank.constants.json_keys import TDRBankJsonKeys
from bps.configio.tdr_bank.dtos import TdrBankCSVRecordsDTO
from bps.configio.tdr_bank.export_interactor import ExportTdrBankInteractor
from bps.configio.tdr_bank.schema import TDR_BANK_SCHEMA


class ExportTdrBankCSVFilesInteractor:
    def __init__(self):
        self.schema = SchemaEngine(schema=TDR_BANK_SCHEMA)

    def get_tdr_bank_csv_files(
        self,
        authority_wise_bank_id_map: Dict[str, str],
        pipeline_item_ids: List[str],
        can_create_csv_files: bool = True,
    ) -> TdrBankCSVRecordsDTO:
        # 1. Get JSON data from export interactor
        interactor = ExportTdrBankInteractor()
        tdr_bank_dict = interactor.export_tdr_bank(
            authority_wise_bank_id_map=authority_wise_bank_id_map,
            pipeline_item_ids=pipeline_item_ids,
        )

        # 2. Extract entities for DTO
        accounts = tdr_bank_dict[TDRBankJsonKeys.ACCOUNTS.value]
        transactions = tdr_bank_dict[TDRBankJsonKeys.TRANSACTIONS.value]
        transaction_logs = tdr_bank_dict[TDRBankJsonKeys.TRANSACTION_LOGS.value]
        note_sheets = tdr_bank_dict[TDRBankJsonKeys.NOTE_SHEETS.value]

        # 3. Transform to CSV format
        json_data = self.schema.transform_flat_data_to_csv(json_data=tdr_bank_dict)

        # 4. Write CSV files if requested
        if can_create_csv_files:
            self._write_to_csv_files(json_data=json_data)

        # 5. Return DTO
        return TdrBankCSVRecordsDTO(
            accounts_records=accounts,
            transactions_records=transactions,
            transaction_logs_records=transaction_logs,
            note_sheets_records=note_sheets,
        )

    def _write_to_csv_files(self, json_data: Dict[str, Any]) -> None:
        csv_writer = CSVWriter()

        for entity_name, records in json_data.items():
            if not records:
                continue

            field_names = self.schema.get_csv_column_names_for_entity(
                entity_name=entity_name
            )

            csv_writer.write_csv(
                file_path=f"{entity_name}.csv",
                records=records,
                fieldnames=field_names,
            )
```

### 5. DTOs (`dtos.py`)

```python
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class TdrBankCSVRecordsDTO:
    accounts_records: List[Dict[str, Any]]
    transactions_records: List[Dict[str, Any]]
    transaction_logs_records: List[Dict[str, Any]]
    note_sheets_records: List[Dict[str, Any]]
```

---

## New Module Creation Checklist

### Step 1: Create Directory Structure
```bash
mkdir -p bps/configio/my_module/constants
touch bps/configio/my_module/__init__.py
touch bps/configio/my_module/constants/__init__.py
```

### Step 2: Define JSON Keys
Create `constants/json_keys.py` with:
- [ ] Top-level entity name enum (e.g., `MyModuleJsonKeys`)
- [ ] Property enums for each entity (e.g., `EntityJsonKeys`)

### Step 3: Create Schema Definition
Create `schema.py` with:
- [ ] Entity schema for each entity type
- [ ] All properties have `type` and `csv_column_name`
- [ ] Foreign key relationships defined
- [ ] Combined schema dictionary at the end

### Step 4: Implement Export Interactor
Create `export_interactor.py` with:
- [ ] Service adapter properties
- [ ] Main export method returning `Dict[str, List[Dict]]`
- [ ] Entity gathering methods in parent-child order
- [ ] ID collection for child entity queries

### Step 5: Implement CSV Export Interactor
Create `export_csv_interactor.py` with:
- [ ] SchemaEngine initialization
- [ ] Main method calling export interactor
- [ ] `transform_flat_data_to_csv()` call
- [ ] CSV file writing logic
- [ ] DTO return with all records

### Step 6: Create DTOs
Create `dtos.py` with:
- [ ] Dataclass for CSV records
- [ ] List fields for each entity type

### Step 7: (If Cross-App) Create Entity Handlers
In the producer app:
- [ ] Entity handler implementing `EntityHandlerInterface`
- [ ] `get_entity_jsons()` method for export
- [ ] GetEntity interactor for data gathering
- [ ] EntityConverter for DTO → JSON
- [ ] Service interface methods for export
- [ ] Storage interface and DbStorageImplementation

In the consumer app:
- [ ] Adapter wrapping the service interface

### Step 8: Test
- [ ] Unit tests for converters
- [ ] Integration tests for export flow
- [ ] Verify CSV output matches schema

---

## Key Files Reference

| Component | File Path |
|-----------|-----------|
| TDR Bank Complete Module | `bps/configio/tdr_bank/` |
| Pipeline Complete Module | `bps/configio/pipeline/` |
| TDR Entity Handlers | `tdr/interactors/configio/` |
| TDR Service Interface | `tdr/app_interfaces/service_interface.py` |
| BPS Adapter | `bps/adapters/tdr_adapter.py` |
| SchemaEngine | `bps/configio/core/schema_engine/schema_engine.py` |
| CSVWriter | `bps/configio/core/csv_utils/csv_writer.py` |
