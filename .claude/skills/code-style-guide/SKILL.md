---
name: code-style-guide
description: Backend development code style guide with enforced rules for Clean Architecture, Clean Code, function limits, exception handling, naming conventions, model standards, and testing. Auto-loaded as context for all code writing tasks.
alwaysApply: true
---

# Backend Code Style Guide

Enforced rules for writing production-ready, maintainable Python code in this Django CRM backend.

## Clean Architecture Rules

### Layer Communication
- **All inter-layer communication uses DTOs or primitives only**
- **No Django model instances cross layer boundaries**
- **Business logic lives in interactors only** — never in models, storage, or GraphQL layer
- **Apps communicate through app interfaces** — never import directly from another app's internals

### Dependency Direction
```
GraphQL → Interactors → Storage Interfaces (abstract)
                      → Adapters (abstract)
Storage Implementations → Storage Interfaces
```

## Clean Code Standards

### Function Limits
```python
# ✅ Functions: max 50 lines, single responsibility
def create_entity(self, params: CreateEntityParamsDTO) -> EntityDTO:
    self._validate_permissions(user_id=params.user_id)
    self._validate_input(name=params.name)
    return self.storage.create_entity(entity_dto=entity_dto)

# ❌ Functions over 50 lines — split into smaller methods
```

### Indentation
```python
# ✅ Maximum 3 levels deep
def process(self, items):
    for item in items:
        if item.is_valid:
            self.storage.save(item)

# ❌ More than 3 levels — extract inner logic
def process(self, items):
    for item in items:
        if item.is_valid:
            for sub in item.subs:
                if sub.active:
                    self.do_thing(sub)  # Too deep
```

### No Flag Arguments
```python
# ✅ Separate methods for different behaviors
def get_active_entities(self): ...
def get_all_entities(self): ...

# ❌ Boolean parameter that alters behavior
def get_entities(self, include_deleted=False): ...
```

### Positive Conditionals
```python
# ✅ Affirmative logic
if buffer.should_compact():

# ❌ Double negation
if not buffer.should_not_compact():
```

### Block Size
```python
# ✅ Max 10 lines per if/else/try/except/while/for block
```

## Naming Conventions

### Classes and Methods
```python
# ✅ Classes: nouns
class PaymentProcessor: ...
class DocumentTemplate: ...

# ✅ Methods: verbs
def calculate_total(self): ...
def validate_input(self): ...
```

### Files
| Component | Pattern | Example |
|---|---|---|
| Interactor | `<verb>_<noun>.py` | `create_document_template.py` |
| Storage Interface | `<domain>_storage_interface.py` | `dms_storage_interface.py` |
| Storage Impl | `<domain>_storage.py` | `dms_storage.py` |
| DTO | `dtos.py` | `dtos.py` (per domain) |

## Exception Handling

```python
# ✅ Specific custom exceptions
from <app>.exceptions.entity_exceptions import EntityNotFoundException
raise EntityNotFoundException(entity_id=entity_id)

# ✅ Catch specific exceptions
try:
    result = external_service.call()
except TimeoutError as e:
    raise ServiceTimeoutError(service="docusign") from e

# ❌ NEVER bare except
try:
    something()
except:
    pass

# ❌ NEVER generic catch-all
try:
    something()
except Exception:
    pass
```

## Enum Usage

```python
# ✅ Use .value at runtime, enum class for typing only
entity_type: EntityType = EntityType.APPLICATION.value
# noinspection PyTypeChecker

# ❌ Never pass raw enum object
entity_type = EntityType.APPLICATION  # Wrong
```

## DTO Rules

```python
# ✅ All DTOs are @dataclass with NO Optional attributes
@dataclass
class EntityDTO:
    entity_id: str
    name: str
    entity_type: str  # Enum class for typing, .value at runtime

# ❌ No Optional attributes
@dataclass
class EntityDTO:
    entity_id: str
    name: Optional[str]  # Wrong — never Optional
```

## Model Standards

```python
# ✅ Always extend AbstractDateTimeCacheModel
# ✅ UUID string primary key
# ✅ Field validators for enums
# ✅ TextField for JSON (not CharField)
# ✅ Soft delete with is_deleted

class Entity(AbstractDateTimeCacheModel):
    id = models.CharField(
        primary_key=True, max_length=255, default=generate_uuid4_str
    )
    config = models.TextField(default="{}")
    is_deleted = models.BooleanField(default=False)
```

## Testing Standards

```python
# ✅ pytest + Factory Boy
# ✅ create_autospec() for mocking
# ✅ Arrange-Act-Assert structure
# ✅ assert_called_once_with() for mock verification
# ✅ Error cases before success cases

# ❌ No MagicMock for DTOs
# ❌ No private helper methods in tests
# ❌ No manual object creation (use factories)
```

## Prohibited Patterns

- **No logging/print in business logic** — no `print()`, `logger.info()`, `logger.debug()`
- **No console output** — business logic produces no stdout/stderr
- **No hasattr checks** — always work with defined schemas
- **No bare except** — always catch specific exceptions
- **No generic try-except** — handle only expected exceptions

## Type Hints

```python
# ✅ Required on ALL parameters and returns
def get_entity(self, entity_id: str) -> EntityDTO:
    ...

# ✅ Use typing module for complex types
from typing import List, Tuple, Dict
def get_entities(self) -> Tuple[List[EntityDTO], int]:
    ...
```

## Implementation Checklist

Before submitting ANY code:
- [ ] All functions under 50 lines
- [ ] Maximum 3 indentation levels
- [ ] No flag arguments
- [ ] DTOs for all layer communication
- [ ] Specific exceptions only
- [ ] Type hints everywhere
- [ ] PEP8 compliant
- [ ] No logging statements
- [ ] Enum.value used at runtime
- [ ] No Optional in DTOs
