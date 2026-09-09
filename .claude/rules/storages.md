---
globs:
  - "**/storages/**"
  - "**/storage_interfaces/**"
---

# Storage Rules

## Inviolable
- Return only **DTOs or primitives** — never return Django model instances
- Implement the corresponding **storage interface** (`abc.ABC`)
- **No business logic** — data access only

## DTO Conversion
Use `@staticmethod` helpers named `_prep_*_dto()` or `_prep_*_dtos()`:
```python
@staticmethod
def _prep_entity_dtos(objs: Iterator[Entity]) -> List[EntityDTO]:
    return [
        EntityDTO(
            entity_id=obj.id, name=obj.name,
            config=json.loads(obj.config),  # deserialize at boundary
        )
        for obj in objs
    ]
```

## Queryset Patterns
- `.values_list("field", flat=True)` for single-column projections
- `.filter(id__in=sorted(id_list))` — sort input IDs for cache efficiency
- `.first()` for optional single lookups (returns `None`, no try-except)
- `.get(id=entity_id)` only when existence is guaranteed or `DoesNotExist` should raise

## Create / Update
```python
def create_entity(self, dto: EntityDTO):
    Entity.objects.create(id=dto.id, name=dto.name, config=json.dumps(dto.config))

def update_entity(self, dto: UpdateEntityDTO):
    obj = Entity.objects.get(id=dto.entity_id)
    if dto.name is not None:
        obj.name = dto.name
    obj.save()
```
- Partial updates: only set non-`None` fields
- JSON serialization (`json.dumps`/`json.loads`) at storage boundary

## Method Signatures (3-arg max)
- **3 arguments max** per method (same rule as `clean-code.md`). Group related fields into a DTO.
- `create_*` methods: accept a single Create DTO (e.g., `CreateEntityDTO`)
- `update_*` methods: accept a single Update DTO (e.g., `UpdateEntityStatusDTO`)
- `get_*` with filters: accept a Filter DTO when 4+ filter params exist (e.g., `EntityFilterDTO`)
- Bulk and singular variants use the same DTO — if `create_bulk` accepts `List[CreateDTO]`, then `create_single` accepts `CreateDTO`

```python
# WRONG — 10 individual arguments
def create_job_execution(self, job_id, job_type, tenant_id, status, ...): ...

# RIGHT — 1 DTO argument
def create_job_execution(self, dto: JobExecutionCreateDTO) -> JobExecutionDTO: ...

# WRONG — 7 optional filter args
def get_job_executions(self, tenant_id, job_type=None, status=None, ...): ...

# RIGHT — 1 filter DTO
def get_job_executions(self, filters: JobExecutionFilterDTO) -> List[JobExecutionDTO]: ...
```

## Bulk Operations
- Map DTOs to dict: `{dto.id: dto for dto in dtos}`
- Fetch with `__in`, loop-and-mutate, then `.bulk_update(fields=[...])`
- `.bulk_create()` for batch inserts
- `@transaction.atomic` + `.select_for_update()` for concurrent writes
