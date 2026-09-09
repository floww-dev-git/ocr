# Storage Interface Patterns Reference

## Basic Storage Interface

```python
import abc
from typing import List, Tuple

from <app>.interactors.<domain>.dtos import (
    EntityDTO,
    CreateEntityParamsDTO,
)
from <app>.dtos import PaginationDTO


class EntityStorageInterface(abc.ABC):
    @abc.abstractmethod
    def create_entity(self, entity_dto: CreateEntityParamsDTO):
        pass

    @abc.abstractmethod
    def get_entity(self, entity_id: str) -> EntityDTO:
        pass

    @abc.abstractmethod
    def get_entities_with_pagination(
        self, pagination: PaginationDTO
    ) -> Tuple[List[EntityDTO], int]:
        pass

    @abc.abstractmethod
    def update_entity_name(self, entity_id: str, name: str):
        pass

    @abc.abstractmethod
    def delete_entity(self, entity_id: str):
        pass

    @abc.abstractmethod
    def is_entity_name_exists(self, name: str) -> bool:
        pass

    @abc.abstractmethod
    def get_valid_entity_ids(self, entity_ids: List[str]) -> List[str]:
        pass
```

## Real Example — DmsStorageInterface (excerpt)

```python
import abc
from typing import List, Optional, Tuple

from plugins.dtos import PaginationDTO
from plugins.interactors.dms.dtos import (
    DocumentDTO,
    DocumentTemplateDTO,
    DocumentTemplateVersionDTO,
    DocumentVersionDTO,
)


class DmsStorageInterface(abc.ABC):
    @abc.abstractmethod
    def is_document_template_name_exists(
        self, pipeline_item_template_id: str, document_template_name: str
    ) -> bool:
        pass

    @abc.abstractmethod
    def create_document_template(self, document_template: DocumentTemplateDTO):
        pass

    @abc.abstractmethod
    def create_document_template_version(
        self, dt_version_dto: DocumentTemplateVersionDTO
    ):
        pass

    @abc.abstractmethod
    def get_pipeline_item_template_admin_doc_template_ids_with_pagination(
        self, pipeline_item_template_id: str, pagination: PaginationDTO
    ) -> Tuple[List[str], int]:
        pass

    @abc.abstractmethod
    def delete_document_template(self, document_template_id: str):
        pass

    @abc.abstractmethod
    def get_document_template_id_for_version_id_bulk(
        self, dt_version_ids: List[str]
    ) -> List["DtVersionIdDTO"]:
        pass
```

## Rules

### Method Categories and Naming

| Category | Prefix | Returns | Example |
|---|---|---|---|
| Create | `create_` | `None` or created ID | `create_entity(dto)` |
| Read single | `get_` | `EntityDTO` | `get_entity(id) -> EntityDTO` |
| Read multiple | `get_` | `List[EntityDTO]` | `get_entities(ids) -> List[EntityDTO]` |
| Read paginated | `get_*_with_pagination` | `Tuple[List[DTO], int]` | `get_entities_with_pagination(pagination)` |
| Update | `update_` | `None` | `update_entity_name(id, name)` |
| Delete | `delete_` | `None` | `delete_entity(id)` |
| Check existence | `is_` | `bool` | `is_name_exists(name) -> bool` |
| Validate IDs | `get_valid_` | `List[str]` | `get_valid_entity_ids(ids) -> List[str]` |
| Bulk operations | `*_bulk` | `List[DTO]` | `get_entities_bulk(ids) -> List[DTO]` |

### File Location
- `<app>/interactors/storage_interfaces/<domain>_storage_interface.py`

### Class Naming
- `<Domain>StorageInterface` (e.g., `DmsStorageInterface`, `TdrStorageInterface`)

### Mandatory Rules
- Always inherit from `abc.ABC`
- Every method has `@abc.abstractmethod` decorator
- Method body is just `pass`
- Parameters and return types fully annotated
- Receive and return DTOs or primitives ONLY — never Django models
- Import DTOs at the top of the file
- One storage interface per domain (can grow large — that's okay)
