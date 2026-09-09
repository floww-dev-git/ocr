# Integration Test Patterns for Pipeline Cloning

Add an integration test to `common/cloning/tests/integration/test_pipeline_cloning.py` using the existing `TestClonePipelineIntegration` class.

Three files need changes:

## 1. Add source data in `common/common_test_setups/pipeline_clone_source_setup.py`

Create source records as a new Phase, linked to the source pipeline.

**Key rules:**
- Place the phase after all its dependency phases
- Populate JSON/TextField fields with IDs of **source** entities so ID remapping can be verified
- Add created objects to the return dict

```python
# Phase N: Your model
from your_app.tests.factories.models import YourModelFactory

your_model = YourModelFactory(
    pipeline_id=pipeline.id,
    config=json.dumps({
        "field_ids": [fields[0].id, fields[1].id],
        "stage_id": stages_data["stages"][0].id,
    }),
)
```

## 2. Add import and assertion call in `test_pipeline_cloning.py`

```python
from your_app.models import YourModel

# In test_clone_pipeline_with_all_entities:
self._assert_cloned_your_models(new_pipeline_id, all_entities)
```

## 3. Add assertion method

### Pattern 1: Simple model (scalar fields only)
```python
@staticmethod
def _assert_cloned_your_models(new_pipeline_id: str) -> None:
    records = list(
        YourModel.objects.filter(
            stage__pipeline_id=new_pipeline_id
        ).values("description", "order", "is_active")
    )
    assert len(records) == 1
    assert records[0] == {
        "description": "Test your model",
        "order": 1,
        "is_active": True,
    }
```

### Pattern 2: Model with remapped FK references
```python
@staticmethod
def _assert_cloned_your_models(new_pipeline_id: str) -> None:
    new_stage_ids = list(
        PipelineStage.objects.filter(
            pipeline_id=new_pipeline_id
        ).values_list("id", flat=True)
    )
    records = list(
        YourModel.objects.filter(stage_id__in=new_stage_ids)
    )
    assert len(records) == 1
    assert records[0].stage_id in [str(sid) for sid in new_stage_ids]
```

### Pattern 3: Model with JSON fields containing remapped IDs

Requires `all_entities` to verify IDs differ from source:

```python
@staticmethod
def _assert_cloned_your_models(
    new_pipeline_id: str, all_entities: dict
) -> None:
    import json

    records = list(YourModel.objects.filter(pipeline_id=new_pipeline_id))
    assert len(records) == 1
    record = records[0]

    # Derive new entity ID sets
    new_stage_ids = set(
        str(sid) for sid in PipelineStage.objects.filter(
            pipeline_id=new_pipeline_id
        ).values_list("id", flat=True)
    )
    source_stage_ids = set(str(s.id) for s in all_entities["stages"])

    # Verify JSON IDs are remapped (new IDs, not source IDs)
    config = json.loads(record.config)
    stage_ids = set(config.get("stage_ids", []))
    assert stage_ids.issubset(new_stage_ids)
    assert stage_ids.isdisjoint(source_stage_ids)
```

## Deriving new entity ID sets — common traversal patterns

| Entity | How to derive new IDs |
|--------|----------------------|
| Stages | `PipelineStage.objects.filter(pipeline_id=new_pipeline_id)` |
| Task Templates | `TaskTemplate.objects.filter(pipeline_id=new_pipeline_id)` |
| Templates | `TaskTemplate → template_id` |
| GoFs | `Template → GoF.objects.filter(template_id__in=...)` |
| Fields | `GoF → Field.objects.filter(gof_id__in=...)` |
| Document Templates | `DocumentTemplate.objects.filter(pipeline_id=new_pipeline_id)` |
| Layouts | `Layout.objects.filter(pipeline_id=new_pipeline_id)` |
| Tabs | `Layout → Tab.objects.filter(layout_id__in=...)` |

## Run the test

```bash
source venv/bin/activate && pytest common/cloning/tests/integration/test_pipeline_cloning.py -v
```
