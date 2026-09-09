# Factory Patterns Reference

## DTO Factory Creation

### Basic DTO Factory

```python
import factory
from <app>.interactors.dtos import CreateFilterSetDTO


class CreateFilterSetDTOFactory(factory.Factory):
    class Meta:
        model = CreateFilterSetDTO

    filter_set_id = factory.Sequence(lambda n: f"filter_set_{n}")
    name = factory.Sequence(lambda n: f"name_{n}")
    filters_logical_operator = LogicalOperator.AND.value
```

**Rules:**
- Inherit from `factory.Factory` for DTOs (NOT `DjangoModelFactory`)
- Set `class Meta: model = <DTOClass>`
- Use `factory.Sequence()` for auto-incrementing string fields
- Use `.value` for enum fields
- Class naming: `<DTOName>Factory`

### Nested DTO Factories

Use `@factory.lazy_attribute` for DTOs that contain lists of other DTOs:

```python
class CreateFilterDTOFactory(factory.Factory):
    class Meta:
        model = CreateFilterDTO

    filter_set_id = factory.Sequence(lambda n: f"filter_set_{n}")
    name = factory.Sequence(lambda n: f"name_{n}")
    conditions_logical_operator = LogicalOperator.AND.value

    @factory.lazy_attribute
    def conditions(self):
        CreateConditionDTOFactory.reset_sequence(1, force=True)
        return CreateConditionDTOFactory.create_batch(size=2)
```

### Sequence Patterns

```python
# String sequences
field_id = factory.Sequence(lambda n: f"field_{n}")
name = factory.Sequence(lambda n: f"name_{n}")
email = factory.Sequence(lambda n: f"user_{n}@example.com")

# Integer sequences
order = factory.Sequence(lambda n: n + 1)
count = factory.Sequence(lambda n: n)

# Boolean (fixed values for defaults)
is_active = True
is_deleted = False
```

### Enum Fields

Always use `.value` for enum fields:

```python
class ExampleDTOFactory(factory.Factory):
    class Meta:
        model = ExampleDTO

    status = Status.ACTIVE.value
    operator = Operator.EQ.value
    logical_operator = LogicalOperator.AND.value
```

## Batch Creation

```python
# Create multiple instances
dtos = CreateFilterSetDTOFactory.create_batch(size=3)

# Batch with overrides
dtos = UserDTOFactory.create_batch(
    size=3,
    role=factory.Iterator(["ADMIN", "USER", "VIEWER"])
)

# Batch with shared field
dtos = FilterDTOFactory.create_batch(
    size=2,
    filter_set_id="shared_filter_set_id"
)
```

## Iterator Pattern

```python
# Cycle through specific values
FilterFactory.create_batch(
    size=len(filter_ids),
    filter_id=factory.Iterator(filter_ids),
    filter_set=factory.Iterator(filter_set_objs),
)

# Iterate enum values
ConditionFactory.create_batch(
    size=3,
    operator=factory.Iterator([
        Operator.EQ.value,
        Operator.GTE.value,
        Operator.LTE.value,
    ])
)
```

## Sequence Reset

### In conftest.py (autouse fixture)

```python
@pytest.fixture(autouse=True, scope="function")
def reset_sequence():
    CreateFilterSetDTOFactory.reset_sequence(1, force=True)
    CreateConditionDTOFactory.reset_sequence(1, force=True)
    UpdateFilterDTOFactory.reset_sequence(1)
```

### Inside lazy_attribute

```python
@factory.lazy_attribute
def conditions(self):
    CreateConditionDTOFactory.reset_sequence(1, force=True)
    return CreateConditionDTOFactory.create_batch(size=2)
```

**Why reset sequences?**
- Ensures deterministic test data across test runs
- Prevents sequence bleed between tests
- Critical for snapshot testing consistency

## Factory File Organization

### Directory Structure

```
<app>/tests/factories/
├── __init__.py
├── interactors/
│   ├── __init__.py
│   ├── filter_dtos.py          # FilterSet, Filter, Condition DTOs
│   ├── collection_dtos.py      # Collection-related DTOs
│   └── view_dtos.py            # View-related DTOs
├── models/
│   ├── __init__.py
│   ├── filter_models.py        # FilterSet, Filter Django model factories
│   └── collection_models.py    # Collection Django model factories
├── adapter_dtos.py             # External service DTO factories
├── presenter_dtos.py           # Presenter response DTO factories
└── storage_dtos.py             # Storage layer DTO factories
```

### Where to Place New Factories

- **Interactor input/output DTOs** -> `factories/interactors/<module>_dtos.py`
- **Django model factories** -> `factories/models/<module>_models.py`
- **Adapter/service DTOs** -> `factories/adapter_dtos.py`
- **Presenter DTOs** -> `factories/presenter_dtos.py`
- **Storage DTOs** -> `factories/storage_dtos.py`

## Avoiding Factory Duplication

Before creating a factory:

1. Search the `tests/factories/` directory for the DTO name
2. Search with: `grep -r "<DTOName>Factory" <app>/tests/`
3. If found, import it from its existing location
4. If not found, create it in the appropriate file per the structure above
5. Never create a second factory for the same DTO class

## Django Model Factories

For integration/interface tests that need database records:

```python
import factory
from <app>.models import FilterSet


class FilterSetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FilterSet

    filter_set_id = factory.Sequence(lambda n: f"filter_set_{n}")
    name = factory.Sequence(lambda n: f"name_{n}")
    filter_ids = json.dumps([])
    filters_logical_operator = LogicalOperator.AND.value
```

**Rules:**
- Inherit from `factory.django.DjangoModelFactory` for Django models
- Use `json.dumps()` for JSON/TextField fields
- Use `factory.SubFactory()` for ForeignKey relationships
