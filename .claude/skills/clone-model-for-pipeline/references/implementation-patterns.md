# Implementation Patterns

## EntityType Section Guide

- Core pipeline configs -> `# ============== CORE PIPELINE ENTITIES ==============`
- Stage-related -> `# ============== STAGE ENTITIES ==============`
- Template-related -> `# ============== TEMPLATE ENTITIES ==============`
- Field-related -> `# ============== FIELD ENTITIES ==============`
- Layout/UI -> `# ============== LAYOUT ENTITIES ==============`
- BPS (application processing) -> `# ============== BPS ENTITIES ==============`
- Automation workflows -> `# ============== AUTOMATION WORKFLOW ENTITIES ==============`
- IB Collections -> `# ============== IB COLLECTIONS ENTITIES ==============`
- Rules -> `# ============== RULE ENTITIES ==============`
- Plugins -> `# ============== PLUGIN ENTITIES ==============`
- Portal entities -> `# ============== PORTAL ENTITIES ==============`

If no section fits, create a new section with the same comment style.

## Decision Tree: Which Methods to Implement

### For `get_dependencies()`

```
Does the model have ONLY Django ForeignKey fields pointing to CloneableModel subclasses?
├── YES, and NO self-referential FKs, NO CharField FKs, NO JSON fields with IDs
│   └── Use Pattern A: super() + explicit declaration
│
├── Has CharField/TextField fields storing entity IDs (e.g., pipeline_id, stage_id)
│   └── Must declare these manually. Use Pattern A: super() + add CharField FKs
│
├── Has JSON TextField fields containing entity IDs
│   └── Use Pattern A or Pattern B depending on self-ref FKs
│
├── Has self-referential ForeignKey (FK to "self")
│   └── DO NOT include self-ref FK in get_dependencies() (causes circular dependency).
│       Declare in get_post_dependencies(). Use Pattern B: build dict from scratch
│
└── Has FKs to non-cloneable models
    └── Exclude those FKs. Use Pattern B or they'll be auto-excluded by super()
```

### For `get_post_dependencies()`

```
Does the model have any of these?
├── Self-referential ForeignKey (FK to "self") → YES -> declare
├── CharField/TextField storing IDs of same entity type → YES -> declare
├── JSON field containing IDs that create circular dependencies → YES -> declare
└── None of the above → No need to implement (base returns {})
```

### For `get_source_queryset()`

```
Can the model's source records be found by filtering on its FK fields?
├── YES -> No override needed
├── NO - needs cross-table join → Override with custom query
├── NO - needs additional filtering → Override, optionally calling super()
└── NO - polymorphic entity_id field → Override with custom filtering
```

### For `get_clone_dependencies()`

```
Are the model's ordering dependencies different from its field dependencies?
├── NO -> No override needed
└── YES -> Override to declare ordering dependencies
```

---

## Code Templates

### Pattern A: Standard Model (super() + explicit declarations)

Use when: Model has Django FKs and/or CharField FKs, NO self-referential FK.

```python
class YourModel(CloneableModel, AbstractCacheModel):
    id = models.CharField(max_length=255, primary_key=True, default=generate_uuid4_str)
    stage = models.ForeignKey(PipelineStage, on_delete=models.CASCADE)
    pipeline_id = models.CharField(max_length=255)

    @classmethod
    def get_entity_type(cls) -> EntityType:
        return EntityType.YOUR_MODEL

    @classmethod
    def get_clone_filter_fields(cls) -> List[str]:
        return [cls.stage.field.name]

    @classmethod
    def get_dependencies(cls) -> Dict[str, Set[EntityType]]:
        dependencies = super().get_dependencies()
        dependencies[cls.stage.field.name] = {EntityType.STAGE}
        dependencies[cls.pipeline_id.field.name] = {EntityType.PIPELINE}
        return dependencies
```

**Real examples:**
- `PipelineStage` (`sales_crm_core/models/stage.py`) — CharField FK to pipeline
- `StageTaskTemplate` (`sales_crm_core/models/stage.py`) — multiple FKs
- `ApplicationConfig` (`bps/models/application_config.py`) — many CharField FKs

### Pattern B: Model with Self-Referential FK (skip super())

Use when: Model has a ForeignKey to "self". Must NOT call super().

```python
class YourModel(CloneableModel, AbstractCacheModel):
    parent_entity = models.ForeignKey(ParentModel, on_delete=models.CASCADE)
    parent_self = models.ForeignKey("self", on_delete=models.SET_NULL, null=True)
    config = models.TextField(null=True)  # JSON with entity IDs

    @classmethod
    def get_dependencies(cls) -> Dict[str, Set[EntityType]]:
        # DO NOT call super() - it would auto-detect parent_self FK
        return {
            cls.parent_entity.field.name: {EntityType.PARENT_ENTITY},
            cls.config.field.name: {EntityType.FIELD, EntityType.STAGE},
        }

    @classmethod
    def get_post_dependencies(cls) -> Dict[str, Set[EntityType]]:
        post_dependencies = super().get_post_dependencies()
        post_dependencies[cls.parent_self.field.name] = {EntityType.YOUR_MODEL}
        return post_dependencies
```

**Real examples:**
- `Node` (`automation_workflows/models/node.py`)
- `Field` (`ib_templates/models/template.py`) — multiple post_dependencies

### Pattern C: JSON Field with Entity IDs (post_dependencies)

```python
@classmethod
def get_post_dependencies(cls) -> Dict[str, Set[EntityType]]:
    return {cls.ordered_field_ids.field.name: {EntityType.FIELD}}
```

**Real examples:** `GoF`, `Template` (`ib_templates/models/template.py`)

### Pattern D: JSON Field with Multiple Entity Types

```python
@classmethod
def get_dependencies(cls) -> Dict[str, Set[EntityType]]:
    dependencies = super().get_dependencies()
    dependencies[cls.config.field.name] = {
        EntityType.FIELD, EntityType.STAGE,
        EntityType.PIPELINE, EntityType.TASK_TEMPLATE,
    }
    return dependencies
```

The cloning system does a string-replace for ALL mappings of ALL listed entity types.

**Real example:** `Tab` (`sales_crm_core/models/layout.py`)

### Pattern E: Custom Source Queryset

Use when: Model cannot be found by simple FK filtering.

```python
@classmethod
def get_clone_filter_fields(cls) -> List[str]:
    return []  # Override get_source_queryset instead

@classmethod
def get_clone_dependencies(cls) -> List[EntityType]:
    return [EntityType.PIPELINE]

@classmethod
def get_source_queryset(cls, context: CloneContext) -> models.QuerySet:
    pipeline_mappings = context.get_all_mappings(EntityType.PIPELINE)
    source_pipeline_ids = list(pipeline_mappings.keys())
    if not source_pipeline_ids:
        return cls.objects.none()
    # Custom query logic
    related_ids = RelatedModel.objects.filter(
        pipeline_id__in=source_pipeline_ids
    ).values_list("your_model_id", flat=True).distinct()
    return cls.objects.filter(id__in=related_ids)
```

**Real examples:**
- `Template` (`ib_templates/models/template.py`) — cross-table join
- `AutomationWorkFlowExecConfig` — filtering by state
- `FeatureToggle` — polymorphic entity_id

### Pattern F: BigAutoField Primary Key

No special method needed. `CloneHelper` auto-detects `AutoField`/`BigAutoField` PKs and skips setting PK on new instances.

**Real example:** `StageTaskTemplateIdentification` (`sales_crm_core/models/stage.py`)

### Pattern G: Empty Dependency Set for Non-Cloneable References

```python
@classmethod
def get_dependencies(cls) -> Dict[str, Set[EntityType]]:
    dependencies = super().get_dependencies()
    dependencies[cls.pipeline_id.field.name] = {EntityType.PIPELINE}
    # variable_ids references non-cloneable entities - empty set means no remapping
    dependencies[cls.variable_ids.field.name] = set()
    return dependencies
```
