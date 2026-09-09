---
name: add-ruleset-with-new-enums
description: Add a new RuleSet with a new RuleSetPurpose, ActionType, and entity_type to the CRM rules engine and wire a private method into a target interactor. Use when you need to add a new rule-driven side effect (stage update, fee trigger, field write, etc.) that is evaluated from rule configs inside an existing interactor.
---

# Add RuleSet with New Enums

Guides adding a **new rule-evaluation side effect** to an existing interactor. This covers keeping the four enum files in sync, writing the private evaluation method, and integrating it into the target flow.

---

## STEP 0 – Gather User Inputs Before Writing Any Code

**ALWAYS ask ALL of the following before touching any file.**

Ask the user to provide:

1. **New `RuleSetPurpose` value** — e.g. `SCRUTINY_STAGE_UPDATE` (need to add to 4 files)
2. **New `ActionType` value** — e.g. `STAGE_UPDATE` (need to add to 4 files)
3. **`RuleEntityType` for rule lookup** — the entity whose rule sets to load, e.g. `PIPELINE_ITEM_TEMPLATE`. Ask if this is a **new** value or one that already exists. (spans 3 files)
4. **`RulesEngineEntityDataSource` for data source** — entity whose field values conditions are evaluated against, e.g. `PIPELINE_ITEM`. Ask if this is a **new** value or one that already exists. (spans 3 files)
5. **Target interactor file path** — e.g. `scrutiny_report/interactors/applications/update_scrutiny_details_in_application.py`
6. **Target interactor class name** — e.g. `UpdateScrutinyDataInApplicationInteractor`
7. **Private method name to write** — e.g. `_update_application_stage`
8. **What the action `config` dict contains** — keys the method should read from the matched rule action's config, e.g. `stage_id`, `stage_field_id`
9. **What to do with the config values** — e.g. call `update_application_field_response_bulk` with an `UpdateFieldIdResponseStrDTO`
10. **Where to call the new method** — which existing method in the class to call it from, and at what point (beginning, after a specific call, or at the end)
11. **`data_source.entity_id` field** — which field on the entity parameter DTO holds the data-source entity's ID (maps to `RulesEngineEntityDataSourceDTO.entity_id`), e.g. `application.application_id`
12. **`entity_ids` field** — which field on the entity parameter DTO holds the rule-lookup entity's ID (passed as `entity_ids`), e.g. `application.application_template_id`

Do not proceed until ALL answers are confirmed.

---

## STEP 1 – Check and Update All Enum Files

There are **four distinct enums** spread across multiple files. For each one, **read every file first**, then only add the value where it is missing.

---

### Enum A: `RuleSetPurpose` — 5 files

| File | Base class |
|---|---|
| `rules_engine/constants.py` | `BaseEnumClass, enum.Enum` |
| `common/constants/rules_engine_enums.py` | `BaseEnumClass, enum.Enum` |
| `bps/constants/rules_engine_enums.py` | `Enum` |
| `bps/adapters/adapter_dtos/rules_engine_enums.py` | `Enum` |
| `scrutiny_report/adapters/rules_engine_dtos.py` | `enum.Enum` |

Check each file for `<NEW_PURPOSE>` in `RuleSetPurpose`. Add only where missing:
```python
<NEW_PURPOSE> = "<NEW_PURPOSE>"
```

---

### Enum B: `ActionType` — 5 files

| File | Base class |
|---|---|
| `rules_engine/constants.py` | `BaseEnumClass, enum.Enum` |
| `common/constants/rules_engine_enums.py` | `BaseEnumClass, enum.Enum` |
| `bps/constants/rules_engine_enums.py` | `Enum` |
| `bps/adapters/adapter_dtos/rules_engine_enums.py` | `Enum` |
| `scrutiny_report/adapters/rules_engine_dtos.py` | `enum.Enum` |

Check each file for `<NEW_ACTION_TYPE>` in `ActionType`. Add only where missing:
```python
<NEW_ACTION_TYPE> = "<NEW_ACTION_TYPE>"
```

---

### Enum C: `RuleEntityType` — 3 files

Only update these if the user confirmed `<RULE_ENTITY_TYPE>` is a **new** value not yet in the codebase.

| File | Base class |
|---|---|
| `common/constants/enums.py` | `BaseEnumClass, enum.Enum` |
| `ib_templates/constants/enums.py` | `BaseEnumClass, enum.Enum` |
| `sales_crm_core/constants/enums.py` | `BaseEnumClass, enum.Enum` |

Check each file for `<RULE_ENTITY_TYPE>` in `RuleEntityType`. Add only where missing:
```python
<RULE_ENTITY_TYPE> = "<RULE_ENTITY_TYPE>"
```

---

### Enum D: `RulesEngineEntityDataSource` — 4 files

Only update these if the user confirmed `<DATA_SOURCE_ENTITY_TYPE>` is a **new** value not yet in the codebase.

| File | Base class |
|---|---|
| `rules_engine/enums.py` | `BaseEnumClass, enum.Enum` |
| `bps/constants/rules_engine_enums.py` | `Enum` |
| `bps/adapters/adapter_dtos/rules_engine_enums.py` | `Enum` |
| `scrutiny_report/adapters/rules_engine_dtos.py` | `enum.Enum` |

Check each file for `<DATA_SOURCE_ENTITY_TYPE>` in `RulesEngineEntityDataSource`. Add only where missing:
```python
<DATA_SOURCE_ENTITY_TYPE> = "<DATA_SOURCE_ENTITY_TYPE>"
```

---

> **Rule**: The string value must be identical across all files. The string IS the database-stored value. Never touch a file where the value already exists.

---

## STEP 2 – Read the Target Interactor and App Adapters

Before writing anything, read:

1. **The target interactor file** — understand existing imports, how other services are exposed as `@property`, the signature of the integration-point method, and any DTOs already imported.
2. **`<app>/adapters/service_adapter.py`** — see which services are already registered and what the `get_service_adapter()` function looks like.
3. **`<app>/adapters/`** directory listing — check whether a `rules_engine_adapter.py` (or equivalent) already exists.

---

## STEP 3 – Create the Rules Engine Adapter (if not present)

### 3a. Check if the adapter file exists

Look for `<app>/adapters/rules_engine_adapter.py`. If it already exists and has `evaluate_entity_rule_sets`, skip to Step 4.

### 3b. Create `<app>/adapters/rules_engine_adapter.py`

Only expose the method needed. Pattern taken from `sales_crm_core/adapters/rules_engine_adapter.py`:

```python
from typing import List

from common.constants.enums import RuleEntityType
from rules_engine.constants import RuleSetPurpose
from rules_engine.interactors.dtos import RulesEngineEntityDataSourceDTO
from rules_engine.interactors.dtos import RuleEngineEvaluationResultDTO


class RulesEngineAdapter:
    @property
    def interface(self):
        from rules_engine.app_interfaces.service_interface import ServiceInterface

        return ServiceInterface()

    def evaluate_entity_rule_sets(
        self,
        entity_type: str,
        entity_ids: List[str],
        purpose: str,
        data_source: RulesEngineEntityDataSourceDTO,
    ) -> RuleEngineEvaluationResultDTO:
        return self.interface.evaluate_entity_rule_sets(
            entity_type=entity_type,
            entity_ids=entity_ids,
            purpose=purpose,
            data_source=data_source,
        )
```

> Keep it minimal — only add the methods this use case actually needs. Do not copy every method from `sales_crm_core`'s adapter.

### 3c. Register in `<app>/adapters/service_adapter.py`

Add a `rules_engine_service` property to the existing `ServiceAdapter` class:

```python
@property
def rules_engine_service(self):
    from <app>.adapters.rules_engine_adapter import RulesEngineAdapter

    return RulesEngineAdapter()
```

---

## STEP 4 – Write the Two Private Methods in the Interactor

### Access rules engine via `@property` on the interactor

Following the same pattern as `sales_crm_service` in the interactor, add:

```python
@property
def rules_engine_service(self):
    from <app>.adapters.service_adapter import get_service_adapter

    return get_service_adapter().rules_engine_service
```

### Correct Call Pattern (from codebase — `tdr` and `bps` modules)

Use the field names confirmed in Step 0 (questions 11 and 12) for `entity_id` and `entity_ids`:

```python
# entity_type, purpose, and data_source entity_type are ALL passed with .value
# <data_source_entity_id>  → <entity_param>.<field from question 11>
# <rule_entity_id>         → <entity_param>.<field from question 12>
data_source = RulesEngineEntityDataSourceDTO(
    entity_id=<data_source_entity_id>,
    entity_type=RulesEngineEntityDataSource.<DATA_SOURCE_ENTITY_TYPE>.value,
)

result = self.rules_engine_service.evaluate_entity_rule_sets(
    entity_type=RuleEntityType.<RULE_ENTITY_TYPE>.value,
    entity_ids=[<rule_entity_id>],
    purpose=RuleSetPurpose.<NEW_PURPOSE>.value,
    data_source=data_source,
)
```

### Correct Traversal Pattern

Only the **first** matching rule per rule set is used:

```python
for rule_set_result in result.rule_set_results.values():
    if not rule_set_result.matching_rules:
        continue
    rule = rule_set_result.matching_rules[0]
    for action in rule.rule_actions:
        if action.action_type == ActionType.<NEW_ACTION_TYPE>.value:
            field_id = action.config.get("<field_id_key>")
            field_response = action.config.get("<field_response_key>")
```

> **Always use `.value`** when comparing `action.action_type` and when passing enum args to `evaluate_entity_rule_sets`.

### Method 1: Orchestrator

Fill in all `<placeholders>` using the values confirmed in Step 0:
- `<data_source_entity_id_field>` → answer to question 11 (e.g. `application.application_id`)
- `<rule_entity_id_field>` → answer to question 12 (e.g. `application.application_template_id`)
- `<application_id_field>` → typically the same as question 11

```python
def <new_method_name>(self, <entity_param>: <EntityDTO>) -> None:
    from rules_engine.interactors.dtos import RulesEngineEntityDataSourceDTO
    from rules_engine.enums import RulesEngineEntityDataSource
    from common.constants.enums import RuleEntityType
    from rules_engine.constants import RuleSetPurpose

    data_source = RulesEngineEntityDataSourceDTO(
        entity_id=<entity_param>.<data_source_entity_id_field>,
        entity_type=RulesEngineEntityDataSource.<DATA_SOURCE_ENTITY_TYPE>.value,
    )

    result = self.rules_engine_service.evaluate_entity_rule_sets(
        entity_type=RuleEntityType.<RULE_ENTITY_TYPE>.value,
        entity_ids=[<entity_param>.<rule_entity_id_field>],
        purpose=RuleSetPurpose.<NEW_PURPOSE>.value,
        data_source=data_source,
    )

    field_response_dtos = self.<_extract_method_name>(result)

    if not field_response_dtos:
        return

    self.sales_crm_service.update_application_field_response_bulk(
        application_id=<entity_param>.<application_id_field>,
        field_response_dtos=field_response_dtos,
    )
```

### Method 2: Extractor (keeps orchestrator under 30 lines)

The extractor returns `List[UpdateFieldIdResponseStrDTO]`. The DTO has three fields:
- `field_id: str`
- `response: Optional[str]`
- `computed_update_config: Optional[ComputedUpdateConfigDTO]` — always `None` here

```python
def <_extract_method_name>(self, result) -> List[UpdateFieldIdResponseStrDTO]:
    from rules_engine.constants import ActionType
    from sales_crm_core.interactors.records.dtos import UpdateFieldIdResponseStrDTO

    dtos = []
    for rule_set_result in result.rule_set_results.values():
        if not rule_set_result.matching_rules:
            continue
        rule = rule_set_result.matching_rules[0]
        for action in rule.rule_actions:
            if action.action_type != ActionType.<NEW_ACTION_TYPE>.value:
                continue
            field_id = action.config.get("<field_id_key>")
            field_response = action.config.get("<field_response_key>")
            if field_id and field_response:
                dtos.append(
                    UpdateFieldIdResponseStrDTO(
                        field_id=field_id,
                        response=field_response,
                        computed_update_config=None,
                    )
                )
    return dtos
```

Fill in all `<placeholders>` using the values confirmed in Step 0.

---

## STEP 5 – Integrate the Call

Using the integration point confirmed in Step 0 (which method, and where), add:

```python
self.<new_method_name>(<entity_param>)
```

Read the target method first to determine exact placement — beginning, after a specific call, or at the end.

---

## STEP 6 – Verify Syntax

```bash
source venv/bin/activate
python -m py_compile rules_engine/constants.py
python -m py_compile common/constants/rules_engine_enums.py
python -m py_compile bps/constants/rules_engine_enums.py
python -m py_compile bps/adapters/adapter_dtos/rules_engine_enums.py
python -m py_compile scrutiny_report/adapters/rules_engine_dtos.py
python -m py_compile <app>/adapters/rules_engine_adapter.py
python -m py_compile <app>/adapters/service_adapter.py
python -m py_compile <target_interactor_path>
```

---

## Common Mistakes to Avoid

| Mistake | Correct Approach |
|---|---|
| Calling `ServiceInterface()` directly inside the interactor | Always go through the app's `rules_engine_service` property |
| Copying all methods from `sales_crm_core`'s adapter | Only expose the methods this use case needs |
| Using a generic service call instead of `sales_crm_service.update_application_field_response_bulk` | The bulk update is always called on `self.sales_crm_service` with `application_id` and `field_response_dtos` |
| Forgetting `computed_update_config=None` in `UpdateFieldIdResponseStrDTO` | The DTO requires all three fields; `computed_update_config` must be explicitly set to `None` |
| Forgetting `.value` when passing enums to `evaluate_entity_rule_sets` | All 3 enum args require `.value` |
| Comparing `action.action_type == ActionType.X` (no `.value`) | Use `action.action_type == ActionType.X.value` |
| Using `first_matching_rule_actions` shortcut | Always iterate `matching_rules → rule.matched → rule.rule_actions` |
| Updating only 1–2 of the 4 enum files | All four must be updated every time |
| Calling `evaluate_entity_rule_sets` inside a loop | Always call once with the full list of entity_ids |
| Not guarding against empty dtos list | Guard with `if not field_response_dtos: return` |
| Hardcoding config values from the rule | Always read from `action.config.get(...)` |
| Hardcoding `entity_id` or `entity_ids` field names without asking the user | Always confirm the exact DTO field names in Step 0 (questions 11 & 12) — they differ per interactor |
| Top-level imports for rules_engine inside the interactor | Keep rules engine imports local to avoid circular imports |

---

## Rule Config Shape (for admin/data setup)

When creating a rule with `action_type = <NEW_ACTION_TYPE>`, its `config` dict must contain the `field_id` and `field_response` keys confirmed in Step 0. Example for a stage update action:

```json
{
  "<field_id_key>": "<uuid of the target field>",
  "<field_response_key>": "<value to set as the field response>"
}
```

The extractor reads `action.config.get("<field_id_key>")` and `action.config.get("<field_response_key>")` and passes them directly as `field_id` and `response` into the output DTO. Document the exact key names for whoever configures rules in the admin or migrations.
