# DTO Patterns Reference

## Basic DTO

```python
from dataclasses import dataclass


@dataclass
class CreateEntityParamsDTO:
    user_id: str
    name: str
    description: str
    entity_type: str  # Use enum class for typing, .value (str) at runtime
```

## DTO with Nested DTOs

```python
from dataclasses import dataclass
from typing import List


@dataclass
class GridUnitDTO:
    text_lines: List[str]
    unit_width: float
    alignment: str  # TextAlignment enum typed


@dataclass
class GridBlockDTO:
    block_id: str
    order: int
    heading: str
    grid_unit_dtos: List[GridUnitDTO]
```

## DTO with Enum Types

```python
from dataclasses import dataclass
from typing import List

from plugins.constants.dms_enums import (
    DocumentTemplateBlockType,
    DocumentTemplateType,
)


@dataclass
class BaseDocumentTemplateBlockDTO:
    block_id: str
    order: int
    block_type: DocumentTemplateBlockType  # typed as enum, but receives .value at runtime


@dataclass
class DocumentTemplateDTO:
    template_id: str
    name: str
    template_type: DocumentTemplateType  # typed as enum
    pipeline_item_template_id: str
    created_by: str
```

## Pagination Return Pattern

```python
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class PaginationDTO:
    offset: int
    limit: int


# Storage interface returns tuple:
# def get_entities(self, pagination: PaginationDTO) -> Tuple[List[EntityDTO], int]:
#     pass  # Returns (entities_list, total_count)
```

## Rules

### Field Ordering
1. ID fields first (`entity_id`, `user_id`)
2. Core data fields next (`name`, `description`, `status`)
3. Relationship fields (`parent_id`, `template_id`)
4. Nested DTO fields last (`block_dtos`, `field_responses`)

### Mandatory Rules
- **NO Optional attributes** — every field is required
- **NO default values** on DTO fields (except very rare cases)
- Always use `@dataclass` decorator
- Use `List[ItemDTO]` for collections, never bare `list`
- Use enum class for type annotation, pass `.value` at runtime
- Import DTOs from the same domain's `dtos.py` file

### File Location
- Domain DTOs: `<app>/interactors/<domain>/dtos.py`
- Shared DTOs: `<app>/dtos.py` (only for cross-domain DTOs)
- Adapter DTOs: `<app>/adapters/dtos/<service>_dtos.py`

### Naming Convention
| Purpose | Pattern | Example |
|---|---|---|
| Input params | `<Action><Entity>ParamsDTO` | `CreateDocumentTemplateParamsDTO` |
| Output result | `<Entity>DTO` | `DocumentTemplateDTO` |
| Intermediate | `<Entity><Detail>DTO` | `DocumentVersionOverviewDetailsDTO` |
| ID-only | `<Entity>IdDTO` | `DtVersionIdDTO` |
