---
globs:
  - "**/models/**"
---

# Model Rules

## Inviolable
- **No business logic** — models define schema only
- **No imports from interactors, storages, or presenters**

## Base Classes
- `AbstractDateTimeCacheModel` — standard for business entities (timestamps + cache)
- `AbstractCacheModel` — for lookup tables without timestamps
- Both use `CustomManager` for cache-aware bulk operations

## Primary Keys
- **CharField with UUID**: `id = models.CharField(primary_key=True, max_length=255, default=generate_uuid4_str)`
- Use `BigAutoField` only for join/config tables (e.g., `ActivityTemplatePipelineConfig`)

## Field Patterns
- **JSON data**: store in `TextField`, not `JSONField` — default `"[]"` or `"{}"`
- **Enum choices**: `choices=MyEnum.get_list_of_tuples()`, default via `MyEnum.VALUE.value`
- **Soft delete**: `is_deleted = models.BooleanField(default=False)` — no `deleted_at`
- **ForeignKey**: always `on_delete=models.CASCADE`, add `null=True, blank=True` for optional
- **Self-referential**: `models.ForeignKey("self", on_delete=models.CASCADE, related_name="children")`

## Query-Driven Fields Are Columns
Any field used in a `WHERE`, dedup lookup, sort, or pagination cursor MUST be an indexed column. JSON `TextField` metadata is reserved for fields that are read together with the row and never filtered on.

- **Column + `db_index=True`** — filter keys (e.g., a `status` exposed via a list/filter endpoint), dedup keys (e.g., a `content_hash` queried for exact-match), sort/cursor keys, polling/monitoring lookups.
- **JSON `TextField` metadata** — read-with-the-row payloads only (rich detail snapshots, nested correlation IDs, audit context). Never the target of a Django ORM filter.
- **No `metadata__contains` LIKE substring scans** in storage — if you find yourself reaching for one, the field belongs in a column.
- **Single source of truth** — when a field is promoted from metadata to a column, it lives ONLY in the column. No dual-write, no metadata mirror, no drift.
- **Append-only migrations** — adding a column to an existing model means a new migration file (`0090_*`), not an in-place edit of an already-committed migration.

**Design-time check (architect + reviewer):** when an ADR or task adds a new field to a model, classify it as queried (column) or read-with-the-row (metadata). If the same ADR defines a list/filter/dedup interactor referencing a field stored in JSON metadata, flag it as a design contradiction before code lands. See `bps/docs/ADR-013-pmu-update-and-transfer.md` § Corrections Log (2026-05-20) for the canonical example.

## Meta Class
- Use `unique_together` for composite uniqueness constraints
- Skip `db_table` — use Django defaults
- Add single-column indexes per the **Query-Driven Fields Are Columns** section above; use `Meta.indexes` only for composite indexes that a single `db_index=True` cannot express

## Validators
- Field-level standalone functions, not class methods
```python
def validate_entity_type(value):
    if value not in [e.value for e in EntityType]:
        raise Exception("Please provide valid entity type")

class MyModel(AbstractDateTimeCacheModel):
    entity_type = models.CharField(max_length=255, validators=[validate_entity_type])
```
