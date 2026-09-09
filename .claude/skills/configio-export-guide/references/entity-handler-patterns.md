# Entity Handler Patterns

Guide for implementing entity handlers, converters, and cross-app service interfaces for configio export.

**Note**: For export-only implementations, methods not needed can raise `NotImplementedError`. The actual `AccountHandler` in the codebase supports both import and export - only `update` methods raise `NotImplementedError`.

## Entity Handler Architecture

```
EntityHandlerInterface[EntityDTO]
├── get_entity_jsons(parent_ids) → Dict     # REQUIRED for export
├── convert_json_to_dto(json) → EntityDTO   # For import (or raise NotImplementedError)
├── run_checks_for_create(dto) → Errors     # For import (or raise NotImplementedError)
├── create(dto) → EntityDTO                 # For import (or raise NotImplementedError)
├── run_checks_for_update(dto) → Errors     # raise NotImplementedError (accounts can't be updated)
└── update(dto) → EntityDTO                 # raise NotImplementedError (accounts can't be updated)

Internal Export Flow:
get_entity_jsons(parent_ids)
├── GetAccounts.get_accounts(bank_ids)      # Orchestrates data gathering
│   ├── Storage.get_accounts_in_banks()     # Fetch DTOs from DB
│   ├── UserService.get_user_profile_bulk() # Get related user data
│   └── AccountConverter.convert_dto_to_json()  # DTO → JSON (EXPORT)
└── Returns Dict[account_id, json_data]
```

## EntityHandlerInterface

### Interface Definition

```python
# bps/configio/core/io_engine/entity_interface.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, TypeVar

EntityDTO = TypeVar("EntityDTO")

class EntityHandlerInterface(ABC, Generic[EntityDTO]):
    @abstractmethod
    def get_entity_jsons(
        self, parent_entity_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Export: Return dict with entity_id as key, JSON as value."""
        pass

    @abstractmethod
    def convert_json_to_dto(self, json: Dict[str, Any]) -> EntityDTO:
        """Import: Convert JSON to domain DTO."""
        pass

    @abstractmethod
    def run_checks_for_create(
        self, entity: EntityDTO
    ) -> List[RunActionErrorDTO]:
        """Import: Validate before creation."""
        pass

    @abstractmethod
    def create(self, entity: EntityDTO):
        """Import: Create entity."""
        pass

    @abstractmethod
    def run_checks_for_update(
        self, entity: EntityDTO
    ) -> List[RunActionErrorDTO]:
        """Import: Validate before update."""
        pass

    @abstractmethod
    def update(self, entity: EntityDTO):
        """Import: Update entity."""
        pass
```

### Actual Implementation (AccountHandler)

```python
# tdr/interactors/configio/account_handler.py

from typing import Any, Dict, List
from bps.configio.core.io_engine.entity_interface import EntityHandlerInterface
from bps.configio.bps_template.dtos import ChangeConfigActionDTO, RunActionErrorDTO
from tdr.interactors.storage_interfaces.dtos import TDRAccountDTO

class AccountHandler(EntityHandlerInterface[TDRAccountDTO]):
    def __init__(
        self,
        storage: StorageInterface,
        custom_object_storage: CustomObjectStorageInterface,
        tdr_bank_storage: TDRBankStorageInterface,
        tdr_bank_io_storage: TDRBankIOStorageInterface,
        tdr_elasticsearch_storage: TDRElasticsearchStorageInterface,
    ):
        self.storage = storage
        self.custom_object_storage = custom_object_storage
        self.tdr_bank_storage = tdr_bank_storage
        self.tdr_bank_io_storage = tdr_bank_io_storage
        self.tdr_elasticsearch_storage = tdr_elasticsearch_storage
        self.account_checker = AccountChecker(storage=tdr_bank_io_storage)

    # EXPORT: Return JSON dictionary
    def get_entity_jsons(
        self, parent_entity_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        from tdr.interactors.configio.account.get_accounts import GetAccounts

        interactor = GetAccounts(
            storage=self.storage,
            custom_object_storage=self.custom_object_storage,
            tdr_bank_io_storage=self.tdr_bank_io_storage,
        )
        return interactor.get_accounts(bank_ids=parent_entity_ids)

    # IMPORT: Convert JSON to DTO
    def convert_json_to_dto(self, json: Dict[str, Any]) -> TDRAccountDTO:
        from tdr.interactors.configio.account.account_converter import AccountConverter

        converter = AccountConverter(
            storage=self.storage,
            custom_object_storage=self.custom_object_storage,
            tdr_bank_io_storage=self.tdr_bank_io_storage,
        )
        return converter.convert_json_to_dto(json=json)

    # IMPORT: Validate before creation
    def run_checks_for_create(
        self, change_config_action_dto: ChangeConfigActionDTO
    ) -> List[RunActionErrorDTO]:
        return self.account_checker.run_checks(
            change_config_action_dto=change_config_action_dto
        )

    # IMPORT: Create entity
    def create(self, change_config_action_dto: ChangeConfigActionDTO):
        from tdr.interactors.accounts.create_tdr_account_without_validation import (
            CreateTDRAccountWithoutValidationInteractor,
        )

        interactor = CreateTDRAccountWithoutValidationInteractor(
            tdr_bank_storage=self.tdr_bank_storage,
            tdr_elasticsearch_storage=self.tdr_elasticsearch_storage,
        )
        return interactor.create_tdr_account_without_validation(
            account=change_config_action_dto.entity_dto
        )

    def validate(self, entity: TDRAccountDTO) -> None:
        raise NotImplementedError()

    # Accounts cannot be updated - raise NotImplementedError
    def run_checks_for_update(
        self, change_config_action_dto: ChangeConfigActionDTO
    ) -> List[RunActionErrorDTO]:
        raise NotImplementedError("Account cannot be updated")

    def update(self, change_config_action_dto: ChangeConfigActionDTO):
        raise NotImplementedError("Account cannot be updated")

    def run_checks_for_update(
        self, entity: TDRAccountDTO
    ) -> List[RunActionErrorDTO]:
        raise NotImplementedError("Import not supported")

    def update(self, entity: TDRAccountDTO):
        raise NotImplementedError("Import not supported")
```

## GetAccounts/GetTransactions Pattern

### Data Gathering Interactor

```python
# tdr/interactors/configio/account/get_accounts.py

from typing import Any, Dict, List
from tdr.interactors.configio.account.account_converter import AccountConverter

class GetAccounts:
    def __init__(
        self,
        storage: StorageInterface,
        custom_object_storage: CustomObjectStorageInterface,
        tdr_bank_io_storage: TDRBankIOStorageInterface,
    ):
        self.tdr_bank_storage = tdr_bank_io_storage
        self.account_converter = AccountConverter(
            storage=storage,
            custom_object_storage=custom_object_storage,
        )

    def get_accounts(
        self, bank_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch accounts and convert to JSON for export."""
        # 1. Fetch storage DTOs
        accounts = self.tdr_bank_storage.get_accounts_in_banks(
            bank_ids=bank_ids
        )
        accounts_map = {account.account_id: account for account in accounts}

        # 2. Fetch related data (avoid N+1 queries)
        holder_user_ids = [account.holder_user_id for account in accounts]
        holder_users_map = self._get_holder_users_map(user_ids=holder_user_ids)

        authority_wise_bank_id_map = (
            self.tdr_bank_storage.get_authority_bank_map()
        )

        # 3. Convert each DTO to JSON using converter
        return {
            account.account_id: self.account_converter.convert_dto_to_json(
                account=account,
                accounts_map=accounts_map,
                holder_users_map=holder_users_map,
                authority_wise_bank_id_map=authority_wise_bank_id_map,
            )
            for account in accounts
        }

    def _get_holder_users_map(
        self, user_ids: List[str]
    ) -> Dict[str, UserProfileDTO]:
        """Bulk fetch user profiles to avoid N+1."""
        from bps.adapters.service_adapter import get_service_adapter

        user_service = get_service_adapter().user_service
        user_profiles = user_service.get_user_profile_bulk(user_ids=user_ids)
        return {
            user_profile.user_id: user_profile
            for user_profile in user_profiles
        }
```

## Entity Converter Pattern

### DTO → JSON Conversion (Export)

```python
# tdr/interactors/configio/account/account_converter.py

from typing import Any, Dict, Optional
from bps.configio.tdr_bank.constants.json_keys import AccountJsonKeys
from common.utils.datetime_utils import convert_datetime_obj_to_string

class AccountConverter:
    def __init__(
        self,
        storage: StorageInterface,
        custom_object_storage: CustomObjectStorageInterface,
    ):
        self.storage = storage
        self.custom_object_storage = custom_object_storage

    def convert_dto_to_json(
        self,
        account: TDRAccountDTO,
        accounts_map: Dict[str, TDRAccountDTO],
        holder_users_map: Dict[str, UserProfileDTO],
        authority_wise_bank_id_map: Dict[str, str],
    ) -> Dict[str, Any]:
        """Transform storage DTO to exportable JSON."""
        # 1. Resolve relationships
        parent_account_no = self._get_parent_account_no(
            account=account,
            accounts_map=accounts_map,
        )

        # 2. Get related entity data
        holder_user = holder_users_map.get(account.holder_user_id)
        phone_number = holder_user.phone_number if holder_user else None

        # 3. Resolve authority from bank ID
        authority = self._get_authority_for_bank(
            bank_id=account.bank_id,
            authority_wise_bank_id_map=authority_wise_bank_id_map,
        )

        # 4. Get file links
        certificate_link = self._get_certificate_link(account)

        # 5. Return JSON with schema-matching keys
        return {
            AccountJsonKeys.TDR_CERTIFICATE_NO.value: account.account_no,
            AccountJsonKeys.AUTHORITY.value: authority,
            AccountJsonKeys.PHONE_NUMBER.value: phone_number,
            AccountJsonKeys.TOTAL_AREA_IN_SQ_YARDS.value: account.initial_balance,
            AccountJsonKeys.TDR_APPLICATION_ID.value: account.creation_ref_id,
            AccountJsonKeys.CREATION_TYPE.value: account.creation_ref_type,
            AccountJsonKeys.ISSUED_DATE_TIME.value: convert_datetime_obj_to_string(
                account.issued_at
            ),
            AccountJsonKeys.PARENT_TDR_CERTIFICATE_NO.value: parent_account_no,
            AccountJsonKeys.CERTIFICATE_LINK.value: certificate_link,
        }

    def _get_parent_account_no(
        self,
        account: TDRAccountDTO,
        accounts_map: Dict[str, TDRAccountDTO],
    ) -> Optional[str]:
        """Resolve parent account reference."""
        if not account.parent_account_id:
            return None

        parent_account = accounts_map.get(account.parent_account_id)
        return parent_account.account_no if parent_account else None

    def _get_authority_for_bank(
        self,
        bank_id: str,
        authority_wise_bank_id_map: Dict[str, str],
    ) -> Optional[str]:
        """Reverse lookup: bank_id → authority name."""
        for authority, mapped_bank_id in authority_wise_bank_id_map.items():
            if mapped_bank_id == bank_id:
                return authority
        return None

    def _get_certificate_link(self, account: TDRAccountDTO) -> Optional[str]:
        """Get certificate file URL from custom objects."""
        if not account.certificate_dtos:
            return None

        # Get latest certificate
        certificate = account.certificate_dtos[-1]
        return self.custom_object_storage.get_file_url(
            file_id=certificate.file_id
        )
```

### Transaction Converter Example

```python
# tdr/interactors/configio/transaction/transaction_converter.py

class TransactionConverter:
    def convert_dto_to_json(
        self,
        transaction: TDRAccountTransactionDTO,
        accounts_map: Dict[str, TDRAccountDTO],
    ) -> Dict[str, Any]:
        """Export transaction to JSON."""
        # Resolve parent reference
        account = accounts_map.get(transaction.account_id)
        account_no = account.account_no if account else None

        # Extract metadata properties
        file_no = self._get_metadata_property(
            transaction=transaction,
            property_id=TransactionJsonKeys.FILE_NO.value,
        )

        return {
            TransactionJsonKeys.TRANSACTION_ID.value: transaction.transaction_id,
            TransactionJsonKeys.TDR_CERTIFICATE_NO.value: account_no,
            TransactionJsonKeys.TRANSACTION_OPERATION.value: transaction.transaction_operation,
            TransactionJsonKeys.STATUS.value: transaction.status,
            TransactionJsonKeys.AREA_REQUESTED.value: transaction.value,
            TransactionJsonKeys.CREATION_DATETIME.value: convert_datetime_obj_to_string(
                transaction.created_at
            ),
            TransactionJsonKeys.FILE_NO.value: file_no,
        }

    def _get_metadata_property(
        self,
        transaction: TDRAccountTransactionDTO,
        property_id: str,
    ) -> Optional[str]:
        """Extract property from transaction metadata."""
        if not transaction.metadata:
            return None
        return transaction.metadata.get(property_id)
```

## Cross-App Service Interface

### Service Interface (Producer App)

```python
# tdr/app_interfaces/service_interface.py

from typing import Any, Dict, List
from tdr.interactors.configio.account_handler import AccountHandler
from tdr.interactors.configio.transaction_handler import TransactionHandler
from tdr.interactors.configio.db_storage_implementation import DbStorageImplementation

class TDRServiceInterface:
    def __init__(self):
        self.storage = self._create_storage()
        self.tdr_bank_storage = self._create_tdr_bank_storage()

    # Export methods for configio

    def get_accounts_json(
        self,
        bank_ids: List[str],
        authority_wise_bank_id_map: Dict[str, str],
    ) -> Dict[str, Dict[str, Any]]:
        """Export accounts as JSON for configio."""
        tdr_bank_io_storage = DbStorageImplementation(
            authority_wise_bank_id_map=authority_wise_bank_id_map
        )

        handler = AccountHandler(
            storage=self.storage,
            custom_object_storage=self.custom_object_storage,
            tdr_bank_io_storage=tdr_bank_io_storage,
        )

        return handler.get_entity_jsons(parent_entity_ids=bank_ids)

    def get_transactions_json_for_accounts(
        self, account_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Export transactions as JSON for configio."""
        storage = DbStorageImplementation()

        handler = TransactionHandler(
            storage=storage,
            tdr_bank_storage=self.tdr_bank_storage,
        )

        return handler.get_entity_jsons(parent_entity_ids=account_ids)

    def get_transaction_logs_json_for_transactions(
        self, transaction_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Export transaction logs as JSON for configio."""
        storage = DbStorageImplementation()

        handler = TransactionLogHandler(storage=storage)

        return handler.get_entity_jsons(parent_entity_ids=transaction_ids)
```

### Adapter (Consumer App)

```python
# bps/adapters/tdr_adapter.py

from typing import Any, Dict, List
from tdr.app_interfaces.service_interface import TDRServiceInterface

class TDRAdapter:
    @property
    def interface(self) -> TDRServiceInterface:
        return TDRServiceInterface()

    # Configio export methods

    def get_accounts_json(
        self,
        bank_ids: List[str],
        authority_wise_bank_id_map: Dict[str, str],
    ) -> Dict[str, Dict[str, Any]]:
        return self.interface.get_accounts_json(
            bank_ids=bank_ids,
            authority_wise_bank_id_map=authority_wise_bank_id_map,
        )

    def get_transactions_json_for_accounts(
        self, account_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        return self.interface.get_transactions_json_for_accounts(
            account_ids=account_ids
        )

    def get_transaction_logs_json_for_transactions(
        self, transaction_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        return self.interface.get_transaction_logs_json_for_transactions(
            transaction_ids=transaction_ids
        )
```

## DbStorageImplementation

```python
# tdr/interactors/configio/db_storage_implementation.py

from typing import Dict, List, Optional
from tdr.interactors.configio.storage_interface import StorageInterface
from tdr.models import TDRAccount, TDRAccountTransaction

class DbStorageImplementation(StorageInterface):
    def __init__(
        self,
        authority_wise_bank_id_map: Optional[Dict[str, str]] = None,
    ):
        self.authority_wise_bank_id_map = authority_wise_bank_id_map or {}

    def get_accounts_in_banks(
        self, bank_ids: List[str]
    ) -> List[TDRAccountDTO]:
        """Fetch accounts from database."""
        accounts = TDRAccount.objects.filter(
            bank_id__in=bank_ids,
            is_deleted=False,
        ).select_related('holder_user')

        return [self._convert_to_dto(account) for account in accounts]

    def get_account_no_by_id(self, account_id: str) -> Optional[str]:
        """Get account number for foreign key resolution."""
        try:
            account = TDRAccount.objects.get(account_id=account_id)
            return account.account_no
        except TDRAccount.DoesNotExist:
            return None

    def get_authority_bank_map(self) -> Dict[str, str]:
        """Return authority → bank_id mapping."""
        return self.authority_wise_bank_id_map

    def _convert_to_dto(self, account: TDRAccount) -> TDRAccountDTO:
        """Convert model to DTO."""
        return TDRAccountDTO(
            account_id=str(account.id),
            account_no=account.account_no,
            bank_id=str(account.bank_id),
            holder_user_id=str(account.holder_user_id),
            initial_balance=account.initial_balance,
            parent_account_id=str(account.parent_account_id) if account.parent_account_id else None,
            issued_at=account.issued_at,
            creation_ref_id=account.creation_ref_id,
            creation_ref_type=account.creation_ref_type,
        )
```

## Configio Storage Interface Pattern

For configio operations, create a **separate storage interface** specific to configio rather than using the app's general storage interface. This allows:
1. **Isolation** - Configio-specific methods separated from general app storage
2. **DB/JSON Implementations** - Different implementations for export (DB) vs import (JSON)
3. **Testability** - Easy to mock for testing

### Storage Interface Definition

```python
# {app}/interactors/{module}/configio/storage_interface.py

import abc
from typing import List
from {app}.interactors.{module}.dtos import EntityDTO


class {Module}ConfigioStorageInterface(abc.ABC):
    @abc.abstractmethod
    def get_entities(
        self, entity_ids: List[str]
    ) -> List[EntityDTO]:
        """Fetch entities for export."""
        pass

    # Add other methods as needed for import operations
```

### DB Storage Implementation (for Export)

```python
# {app}/interactors/{module}/configio/db_storage_implementation.py

from typing import List
from {app}.interactors.{module}.configio.storage_interface import (
    {Module}ConfigioStorageInterface,
)
from {app}.interactors.{module}.dtos import EntityDTO
from {app}.storages.{module}_storage import {Module}Storage


class {Module}DbStorageImplementation({Module}ConfigioStorageInterface):
    def __init__(self):
        self._storage = {Module}Storage()

    def get_entities(
        self, entity_ids: List[str]
    ) -> List[EntityDTO]:
        return self._storage.get_entity_dtos(entity_ids=entity_ids)
```

### Service Interface Usage

```python
# {app}/app_interfaces/service_interface.py

def get_entities_json(
    self, entity_ids: List[str]
) -> Dict[str, Dict[str, Any]]:
    from {app}.interactors.{module}.configio.db_storage_implementation import (
        {Module}DbStorageImplementation,
    )
    from {app}.interactors.{module}.configio.entity_handler import (
        EntityHandler,
    )

    configio_storage = {Module}DbStorageImplementation()
    handler = EntityHandler(configio_storage=configio_storage)
    return handler.get_entity_jsons(parent_entity_ids=entity_ids)
```

### Handler Using Configio Storage

```python
# {app}/interactors/{module}/configio/entity_handler.py

class EntityHandler(EntityHandlerInterface[EntityDTO]):
    def __init__(self, configio_storage: {Module}ConfigioStorageInterface):
        self.configio_storage = configio_storage

    def get_entity_jsons(
        self, parent_entity_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        dtos = self.configio_storage.get_entities(
            entity_ids=parent_entity_ids
        )
        # Convert to JSON...
```

## Key Files Reference

| Component | File Path |
|-----------|-----------|
| EntityHandlerInterface | `bps/configio/core/io_engine/entity_interface.py` |
| AccountHandler | `tdr/interactors/configio/account_handler.py` |
| GetAccounts | `tdr/interactors/configio/account/get_accounts.py` |
| AccountConverter | `tdr/interactors/configio/account/account_converter.py` |
| TransactionHandler | `tdr/interactors/configio/transaction_handler.py` |
| TDRBankIOStorageInterface | `tdr/interactors/configio/storage_interface.py` |
| DbStorageImplementation | `tdr/interactors/configio/db_storage_implementation.py` |
| TDRServiceInterface | `tdr/app_interfaces/service_interface.py` |
| TDRAdapter | `bps/adapters/tdr_adapter.py` |
