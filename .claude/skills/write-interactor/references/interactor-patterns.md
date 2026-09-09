# Interactor Patterns Reference

## Basic Interactor with Single Storage

```python
from plugins.interactors.dms.dtos import AdminDocumentTemplateDTO
from plugins.interactors.mixins.dms_mixin import DmsMixin
from plugins.interactors.storage_interfaces.dms_storage_interface import (
    DmsStorageInterface,
)


class DeleteDocumentTemplateInteractor(DmsMixin):
    def __init__(self, dms_storage: DmsStorageInterface):
        self.dms_storage = dms_storage

    def delete_document_template(
        self,
        user_id: str,
        document_template_id: str,
    ) -> AdminDocumentTemplateDTO:
        self.validate_document_template_admin_permission(
            document_template_id=document_template_id,
            user_id=user_id,
            dms_storage=self.dms_storage,
        )

        self.dms_storage.delete_document_template(
            document_template_id=document_template_id
        )
        return self._get_latest_version_admin_document_templates(
            doc_template_id=document_template_id
        )

    def _get_latest_version_admin_document_templates(
        self, doc_template_id: str
    ) -> AdminDocumentTemplateDTO:
        from plugins.interactors.dms.get_latest_version_admin_document_templates import (
            GetLatestVersionAdminDocumentTemplatesInteractor,
        )

        interactor = GetLatestVersionAdminDocumentTemplatesInteractor(
            dms_storage=self.dms_storage
        )

        return interactor.get_latest_version_admin_document_templates(
            document_template_ids=[doc_template_id]
        )[0]
```

## Key Patterns

### Constructor — Dependency Injection
```python
class SomeInteractor:
    def __init__(
        self,
        entity_storage: EntityStorageInterface,
        config_storage: ConfigStorageInterface,
    ):
        self.entity_storage = entity_storage
        self.config_storage = config_storage
```

### Mixin Usage
```python
from <app>.interactors.mixins.iam_mixin import IamMixin

class SomeInteractor(IamMixin):
    def do_work(self, user_id: str, entity_id: str):
        # Mixin method for permission validation
        self.validate_user_permission(
            user_id=user_id,
            entity_id=entity_id,
        )
        # ... business logic
```

### Lazy Import for Interactor-to-Interactor Calls
```python
def _delegate_to_other(self, entity_id: str) -> SomeDTO:
    from <app>.interactors.<domain>.<module> import OtherInteractor

    interactor = OtherInteractor(
        entity_storage=self.entity_storage
    )
    return interactor.process(entity_id=entity_id)
```

### Service Adapter via @property
```python
@property
def _iam_interface(self):
    from iam.app_interfaces.iam_interface import IamInterface
    return IamInterface()

def do_work(self, user_id: str):
    account_id = self._iam_interface.get_pipeline_account_id(
        user_id=user_id
    )
```

### Enum Value Usage
```python
# ✅ CORRECT — always use .value at runtime
entity_type = PipelineItemType.APPLICATION.value
# noinspection PyTypeChecker
dto = EntityDTO(entity_type=entity_type)

# ❌ WRONG — never pass raw enum object
dto = EntityDTO(entity_type=PipelineItemType.APPLICATION)
```

### Exception Raising
```python
# ✅ CORRECT — specific custom exception
from <app>.exceptions.entity_exceptions import EntityNotFoundException

if not valid_ids:
    raise EntityNotFoundException(entity_id=entity_id)

# ❌ WRONG — bare exception or generic
except Exception:
    pass
```

## File Naming Convention

| Component | Pattern | Example |
|---|---|---|
| Interactor file | `<verb>_<noun>.py` | `create_document_template.py` |
| Interactor class | `<Verb><Noun>Interactor` | `CreateDocumentTemplateInteractor` |
| Public method | `<verb>_<noun>` | `create_document_template()` |
| Private method | `_<verb>_<noun>` | `_validate_template_name()` |

## Method Flow Template

```python
def create_entity(self, params: CreateEntityParamsDTO) -> EntityDTO:
    # 1. Permission validation
    self.validate_admin_permission(user_id=params.user_id)

    # 2. Input validation
    self._validate_entity_name(name=params.name)

    # 3. Business rule checks
    is_duplicate = self.entity_storage.is_entity_name_exists(
        name=params.name
    )
    if is_duplicate:
        raise DuplicateEntityNameError(name=params.name)

    # 4. Storage operations
    self.entity_storage.create_entity(entity_dto=entity_dto)

    # 5. Side effects (events, notifications)
    self._trigger_entity_created_event(entity_id=entity_dto.id)

    # 6. Return result
    return entity_dto
```
