---
name: clone-model-for-pipeline
description: Make any Django model cloneable as part of pipeline cloning. Covers adding EntityType enum values, inheriting CloneableModel, implementing required/optional methods, handling edge cases (JSON fields with IDs, self-referential FKs, custom querysets, BigAutoField PKs), registering in the pipeline cloneable entities list, and writing integration tests to verify cloning correctness.
argument-hint: "[model name or path to model file]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Edit, Write
---

# Clone Model for Pipeline

Step-by-step guide for making any Django model participate in pipeline cloning using the generic cloning framework at `common/cloning/`.

## Framework Architecture

| Component | File | Purpose |
|-----------|------|---------|
| `CloneableModel` | `common/cloning/base.py` | Abstract base class models inherit from |
| `EntityType` | `common/cloning/enums.py` | Enum registry of all cloneable entity types |
| `CloneHelper` | `common/cloning/helpers.py` | Bulk clone and field update utilities |
| `CloneOrchestrator` | `common/cloning/orchestrator.py` | Coordinates cloning in dependency order |
| `CloneRegistry` | `common/cloning/registry.py` | Auto-discovers CloneableModel subclasses |
| `DependencyResolver` | `common/cloning/resolver.py` | Topological sort for execution order |
| `CloneContext` | `common/cloning/context.py` | Shared old-ID-to-new-ID mapping store |
| `ClonePipelineInteractor` | `common/cloning/clone_pipeline_interactor.py` | Pipeline-specific cloning entry point |

### How Cloning Works

1. `CloneOrchestrator` clones the root entity (Pipeline) first
2. `DependencyResolver` sorts remaining entities by their `get_clone_dependencies()`
3. For each entity in order, `clone()` is called which:
   - Calls `get_source_queryset()` to find source records
   - Calls `CloneHelper.bulk_clone()` which copies each instance, generates new PKs, and remaps FK values using `get_dependencies()`
   - Stores old->new ID mappings in `CloneContext`
4. After all entities are cloned, `post_clone_update()` runs for entities with circular dependencies declared in `get_post_dependencies()`

## Prerequisites Checklist

- [ ] The model has a relationship to the pipeline (direct or through parent entities)
- [ ] You know the model's primary key type (CharField with UUID vs BigAutoField vs default AutoField)
- [ ] You've identified all FK fields that point to other cloneable models
- [ ] You've identified any CharField/TextField fields that store IDs of other cloneable entities
- [ ] You've identified any JSON fields (TextField) that contain entity IDs
- [ ] You've identified any self-referential ForeignKey fields

## Step-by-Step Guide

### Step 1: Add EntityType to `common/cloning/enums.py`

Add a new enum value under the appropriate section comment. See [references/implementation-patterns.md](references/implementation-patterns.md) for section guide.

### Step 2: Register in `get_pipeline_cloneable_entities()`

In the same file, add your entity type under the matching section. Order after dependencies.

### Step 3: Update Model Inheritance

```python
from common.cloning.base import CloneableModel
from common.cloning.enums import EntityType

class YourModel(CloneableModel, ...existing_bases...):
    ...
```

### Step 4: Implement `get_entity_type()`

```python
@classmethod
def get_entity_type(cls) -> EntityType:
    return EntityType.YOUR_MODEL
```

### Step 5: Implement `get_clone_filter_fields()`

```python
@classmethod
def get_clone_filter_fields(cls) -> List[str]:
    return [cls.parent_fk.field.name]
```

### Step 6: Implement `get_dependencies()`

Use the Decision Tree in [references/implementation-patterns.md](references/implementation-patterns.md) to determine the correct pattern (A through G).

### Step 7: Handle Special Cases

Use `get_post_dependencies()`, custom `get_source_queryset()`, or other overrides as needed. See [references/implementation-patterns.md](references/implementation-patterns.md).

### Step 8: Add Integration Test

See [references/test-patterns.md](references/test-patterns.md) for the full testing guide.

## Field Reference Syntax

Always use `cls.<field_name>.field.name` for refactor-safe field references:
```python
cls.pipeline_id.field.name    # -> "pipeline_id"
cls.stage.field.name          # -> "stage" (FK resolves to field name without _id)
cls.config.field.name         # -> "config"
```

## Verification Checklist

- [ ] **EntityType enum** added in `common/cloning/enums.py` under the correct section
- [ ] **Registered** in `get_pipeline_cloneable_entities()` in the same file
- [ ] **Model inherits** `CloneableModel` (added to base classes)
- [ ] **`get_entity_type()`** returns the correct `EntityType` value
- [ ] **`get_clone_filter_fields()`** returns the right FK field(s) (or empty list with custom queryset)
- [ ] **`get_dependencies()`** declares ALL fields containing cloneable entity IDs
- [ ] **Self-referential FKs** are in `get_post_dependencies()`, NOT in `get_dependencies()`
- [ ] **JSON fields with circular refs** are in `get_post_dependencies()`
- [ ] **Custom queryset** overrides `get_source_queryset()` if needed
- [ ] **Integration test** added and passes
