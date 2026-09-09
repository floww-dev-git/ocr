# Export Interactor Patterns

Comprehensive guide for implementing export interactors that gather data and transform it to CSV format.

## Export Flow Architecture

```
ExportInteractor (Data Gathering)
├── Fetches data from service adapters or entity handlers
├── Collects entity IDs for child queries
├── Returns Dict[str, List[Dict]] with entity names as keys

ExportCSVInteractor (CSV Transformation)
├── Calls ExportInteractor to get JSON data
├── Uses SchemaEngine.transform_flat_data_to_csv()
├── Writes CSV files using CSVWriter
└── Returns typed DTO with all records
```

## Export Interactor Pattern

### Basic Structure

```python
from typing import Any, Dict, List
from bps.adapters.service_adapter import get_service_adapter
from bps.configio.tdr_bank.constants.json_keys import TDRBankJsonKeys

class ExportTdrBankInteractor:
    @property
    def tdr_service(self) -> TDRAdapter:
        return get_service_adapter().tdr

    @property
    def sales_crm_service(self) -> SalesCrmService:
        return get_service_adapter().sales_crm_service

    def export_tdr_bank(
        self,
        authority_wise_bank_id_map: Dict[str, str],
        pipeline_item_ids: List[str],
    ):
        # 1. Gather root entities (accounts)
        accounts_json, account_ids = self.get_accounts_json(
            authority_wise_bank_id_map=authority_wise_bank_id_map
        )

        # 2. Gather child entities (transactions)
        transactions_json, transaction_ids = self.get_transactions_json(
            account_ids=account_ids
        )

        # 3. Gather grandchild entities (transaction logs)
        transaction_logs_json = self.get_transaction_logs_json(
            transaction_ids=transaction_ids
        )

        # 4. Gather related entities (note sheets)
        note_sheets_json = self.get_note_sheets_json(
            pipeline_item_ids=pipeline_item_ids
        )

        # Return with entity names as keys (values are already lists)
        return {
            TDRBankJsonKeys.ACCOUNTS.value: accounts_json,
            TDRBankJsonKeys.TRANSACTIONS.value: transactions_json,
            TDRBankJsonKeys.TRANSACTION_LOGS.value: transaction_logs_json,
            TDRBankJsonKeys.NOTE_SHEETS.value: note_sheets_json,
        }

    def get_accounts_json(
        self, authority_wise_bank_id_map: Dict[str, str]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        bank_ids = list(authority_wise_bank_id_map.values())

        # Call service adapter (cross-app communication)
        accounts = self.tdr_service.get_accounts_json(
            bank_ids=bank_ids,
            authority_wise_bank_id_map=authority_wise_bank_id_map,
        )

        # Returns (list of jsons, list of account_ids)
        return list(accounts.values()), list(accounts.keys())

    def get_transactions_json(
        self, account_ids: List[str]
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        transactions = self.tdr_service.get_transactions_json_for_accounts(
            account_ids=account_ids,
        )

        return list(transactions.values()), list(transactions.keys())

    def get_transaction_logs_json(
        self, transaction_ids: List[str]
    ) -> List[Dict[str, Any]]:
        transaction_logs = self.tdr_service.get_transaction_logs_json_for_transactions(
            transaction_ids=transaction_ids,
        )

        return list(transaction_logs.values())

    def get_note_sheets_json(
        self, pipeline_item_ids: List[str]
    ) -> List[Dict[str, Any]]:
        note_sheets = self.sales_crm_service.get_pipeline_item_remarks_json_bulk(
            pipeline_item_ids=pipeline_item_ids
        )

        return list(note_sheets.values())
```

### Complex Export with Multiple Sources (Pipeline)

```python
class ExportPipelineInteractor:
    def __init__(
        self,
        assign_a_friend_storage: AssignFriendConfigStorageInterface,
        application_config_storage: ApplicationConfigStorageInterface,
    ):
        self.schema = SchemaEngine(BPS_PIPELINES_SCHEMA)
        self.assign_a_friend_storage = assign_a_friend_storage
        self.application_config_storage = application_config_storage

    @property
    def sales_crm_service(self) -> SalesCrmService:
        return get_service_adapter().sales_crm_service

    def export_pipelines(
        self, pipeline_item_template_id: str
    ) -> Dict[str, Any]:
        # 1. Get root entity IDs
        pipeline_ids = self.get_pipeline_ids(
            pipeline_item_template_id=pipeline_item_template_id
        )

        # 2. Gather from multiple sources
        pipelines = self._get_pipelines_json(pipeline_ids=pipeline_ids)
        stage_jsons = self._get_stage_jsons(pipeline_ids=pipeline_ids)
        conditional_action_rules = self._get_conditional_action_rules_json(
            pipeline_ids=pipeline_ids,
            pipeline_item_template_id=pipeline_item_template_id,
        )
        stage_transitions = self._get_stage_transitions_json(
            pipeline_ids=pipeline_ids
        )

        # 3. Return combined data
        return {
            PipelineConfigJsonKeys.PIPELINES.value: pipelines,
            **stage_jsons,  # Spreads stages, display_stages
            PipelineConfigJsonKeys.CONDITIONAL_ACTION_RULES.value: conditional_action_rules,
            PipelineConfigJsonKeys.STAGE_TRANSITIONS.value: stage_transitions,
        }

    def get_pipeline_ids(self, pipeline_item_template_id: str) -> List[str]:
        (template_pipeline_ids, _) = (
            self.sales_crm_service.get_pipeline_ids_to_pipeline_item_templates(
                pipeline_item_template_ids=[pipeline_item_template_id]
            )
        )
        return [dto.pipeline_id for dto in template_pipeline_ids]

    @staticmethod
    def _get_stage_jsons(pipeline_ids: List[str]) -> Dict[str, Any]:
        interactor = GetStageJsonsBulk()
        return interactor.get_stage_jsons_bulk(pipeline_ids=pipeline_ids)
```

## CSV Export Interactor Pattern

### Basic Structure

```python
from dataclasses import dataclass
from typing import Any, Dict, List

from bps.configio.core.schema_engine import SchemaEngine
from bps.configio.core.csv_utils import CSVWriter
from bps.configio.tdr_bank.constants.json_keys import TDRBankJsonKeys
from bps.configio.tdr_bank.schema import TDR_BANK_SCHEMA

@dataclass
class TdrBankCSVRecordsDTO:
    accounts_records: List[Dict[str, Any]]
    transactions_records: List[Dict[str, Any]]
    transaction_logs_records: List[Dict[str, Any]]
    note_sheets_records: List[Dict[str, Any]]


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

        # 2. Extract entities for DTO return
        accounts = tdr_bank_dict[TDRBankJsonKeys.ACCOUNTS.value]
        transactions = tdr_bank_dict[TDRBankJsonKeys.TRANSACTIONS.value]
        transaction_logs = tdr_bank_dict[TDRBankJsonKeys.TRANSACTION_LOGS.value]
        note_sheets = tdr_bank_dict[TDRBankJsonKeys.NOTE_SHEETS.value]

        # 3. Transform to CSV format using schema
        json_data = self.schema.transform_flat_data_to_csv(json_data=tdr_bank_dict)

        # 4. Write CSV files if requested
        if can_create_csv_files:
            self._write_to_csv_files(json_data=json_data)

        # 5. Return DTO for in-memory use
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

            # Get CSV column names from schema
            field_names = self.schema.get_csv_column_names_for_entity(
                entity_name=entity_name
            )

            # Write CSV file
            csv_writer.write_csv(
                file_path=f"{entity_name}.csv",
                records=records,
                fieldnames=field_names,
            )
```

## SchemaEngine Transform Method

The `transform_flat_data_to_csv()` method handles:

1. **Property ID → CSV Column Name mapping**
2. **Type coercion** (boolean → YES/NO)
3. **Value transformation**

```python
def transform_flat_data_to_csv(self, json_data: Dict) -> Dict:
    transformed_data = {}

    for entity_name, entity_list in json_data.items():
        properties = self.find_entity_properties(entity_name=entity_name)

        transformed_entity_list = []
        for entity_data in entity_list:
            transformed_entity_data = {}

            for property_key, value in entity_data.items():
                property_config = properties.get(property_key)
                if not property_config:
                    continue

                # Transform value based on type
                value = self.transform_property_value_to_csv(
                    property_config=property_config,
                    value=value,
                )

                # Map property_id to csv_column_name
                csv_column_name = self.get_csv_column_name(
                    entity_name=entity_name,
                    property_id=property_key,
                )

                transformed_entity_data[csv_column_name] = value

            transformed_entity_list.append(transformed_entity_data)

        transformed_data[entity_name] = transformed_entity_list

    return transformed_data

@staticmethod
def transform_property_value_to_csv(property_config: Dict, value: Any) -> Any:
    property_type = property_config.get(SchemaKey.TYPE.value)

    # Boolean → YES/NO transformation
    if property_type == SchemaDataType.BOOLEAN.value:
        value = BooleanFromSheetsEnum.YES.value if value is True else BooleanFromSheetsEnum.NO.value

    return value
```

## Error Handling Patterns

```python
class ExportInteractor:
    def export_data(self, parent_ids: List[str]) -> Dict[str, List[Dict]]:
        if not parent_ids:
            return self._get_empty_result()

        try:
            accounts_json = self._get_accounts_json(parent_ids)
        except ExternalServiceError as e:
            raise ExportError(
                f"Failed to fetch accounts: {str(e)}"
            ) from e

        return {
            EntityJsonKeys.ACCOUNTS.value: list(accounts_json.values()),
        }

    def _get_empty_result(self) -> Dict[str, List[Dict]]:
        return {
            EntityJsonKeys.ACCOUNTS.value: [],
            EntityJsonKeys.TRANSACTIONS.value: [],
        }
```

## Key Files Reference

| Component | File Path |
|-----------|-----------|
| SchemaEngine | `bps/configio/core/schema_engine/schema_engine.py` |
| CSVWriter | `bps/configio/core/csv_utils/csv_writer.py` |
| TDR Bank Export | `bps/configio/tdr_bank/export_interactor.py` |
| TDR Bank CSV Export | `bps/configio/tdr_bank/export_csv_interactor.py` |
| Pipeline Export | `bps/configio/pipeline/export_interactor.py` |
| TDR Bank DTOs | `bps/configio/tdr_bank/dtos.py` |
