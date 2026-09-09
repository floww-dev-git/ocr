# Model Patterns Reference

## Complete Model Example (from plugins/models/dms.py)

```python
from typing import Dict, List, Set

from django.db import models

from common.cloning.base import CloneableModel
from common.cloning.context import CloneContext
from common.cloning.enums import EntityType
from common.constants.enums import PipelineItemType
from common.models.cache_abstract_models import AbstractDateTimeCacheModel
from common.utils import generate_uuid4_str
from plugins.constants.dms_enums import (
    DocumentTemplateType,
    DocumentVersionState,
)


def validate_pipeline_item_type(value):
    if value not in PipelineItemType.get_list_of_values():
        raise ValueError(f"Invalid crm entity type: {value}")


def validate_document_template_type(value):
    if value not in DocumentTemplateType.get_list_of_values():
        raise ValueError(f"Invalid document template type: {value}")


class DocumentTemplate(AbstractDateTimeCacheModel):
    id = models.CharField(
        primary_key=True, max_length=255, default=generate_uuid4_str
    )
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    pipeline_item_template_id = models.CharField(max_length=255)
    pipeline_id = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.CharField(max_length=255)
    template_type = models.CharField(
        max_length=255, validators=[validate_document_template_type]
    )
    is_deleted = models.BooleanField(default=False)
    variable_ids = models.TextField(default="[]")
    border_style = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        validators=[validate_document_border_style],
    )
```

## Field Type Patterns

### UUID Primary Key (MANDATORY for all models)
```python
id = models.CharField(
    primary_key=True, max_length=255, default=generate_uuid4_str
)
```

### String Fields
```python
# Required string
name = models.CharField(max_length=255)

# Optional string
description = models.TextField(null=True, blank=True)

# String with enum validation
status = models.CharField(
    max_length=255, validators=[validate_status]
)
```

### JSON Fields (ALWAYS use TextField)
```python
# JSON object config
config = models.TextField(default="{}")

# JSON array
variable_ids = models.TextField(default="[]")

# Document what the JSON stores:
# config stores: {"key1": "value", "key2": ["item1", "item2"]}
```

### Boolean Fields
```python
is_deleted = models.BooleanField(default=False)
is_active = models.BooleanField(default=True)
is_enabled = models.BooleanField(default=False)
```

### Date Fields
```python
published_at = models.DateTimeField(null=True, blank=True)
generated_at = models.DateTimeField(auto_now_add=True)
```

### Foreign Key as String ID
```python
# ✅ CORRECT — use CharField for FK references
pipeline_item_id = models.CharField(max_length=255)
created_by = models.CharField(max_length=255)

# ❌ AVOID — Django ForeignKey creates tight coupling
# pipeline_item = models.ForeignKey(PipelineItem, on_delete=models.CASCADE)
```

### Actual Django ForeignKey (only when cascade delete needed)
```python
document_template = models.ForeignKey(
    DocumentTemplate,
    on_delete=models.CASCADE,
    related_name="versions",
)
```

## Validator Functions

```python
# Always place validators above model class in the same file

def validate_entity_type(value):
    from <app>.constants.enums import EntityType
    if value not in EntityType.get_list_of_values():
        raise ValueError(f"Invalid entity type: {value}")


def validate_status(value):
    from <app>.constants.enums import StatusEnum
    if value not in StatusEnum.get_list_of_values():
        raise ValueError(f"Invalid status: {value}")
```

## Index Patterns

```python
class Meta:
    # Single field index
    indexes = [
        models.Index(
            fields=["pipeline_item_id"],
            name="idx_doc_pipeline_item",
        ),
    ]

    # Composite index for common query
    indexes = [
        models.Index(
            fields=["pipeline_item_id", "is_deleted"],
            name="idx_doc_pi_deleted",
        ),
    ]

    # Unique constraint
    unique_together = [
        ("account_id", "plugin_type"),
    ]
```

## CloneableModel Pattern (if model needs pipeline cloning support)

```python
from common.cloning.base import CloneableModel
from common.cloning.context import CloneContext
from common.cloning.enums import EntityType


class DocumentTemplate(CloneableModel, AbstractDateTimeCacheModel):
    # ... fields ...

    @classmethod
    def get_entity_type(cls) -> EntityType:
        return EntityType.DOCUMENT_TEMPLATE

    @classmethod
    def get_dependencies(cls) -> List[type]:
        return []  # Models that must be cloned first

    def clone(self, context: CloneContext) -> "DocumentTemplate":
        # Implement cloning logic
        pass
```

## OneToOne Relationship Pattern

```python
class KnowlarityAccountConfig(AbstractDateTimeCacheModel):
    id = models.CharField(
        primary_key=True, max_length=255, default=generate_uuid4_str
    )
    plugin_service_account = models.OneToOneField(
        PluginServiceAccount,
        on_delete=models.CASCADE,
        related_name="knowlarity_config",
    )
    application_access_key = models.CharField(max_length=255)
```

## Model Naming Convention

| Entity | Model Name | File Name |
|---|---|---|
| Document Template | `DocumentTemplate` | `dms.py` or `document_template.py` |
| Plugin Service Account | `PluginServiceAccount` | `plugin.py` |
| WhatsApp Phone Number | `WhatsAppBusinessPhoneNumber` | `whatsapp.py` |
