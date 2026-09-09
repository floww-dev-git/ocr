---
description: ConfigIO architecture rules for CSV import/export modules
globs:
  - "**/configio/**"
  - "**/populate/**"
---

# ConfigIO Architecture

ConfigIO features (CSV import/export) split responsibility across two apps: the **IO orchestrator** (`bps`) and the **owning app** — whichever app owns the entity's domain logic. The owning app is NOT fixed: verified examples include `sales_crm_core`, `tdr`, `portals`, `rules_engine`, and `bps` itself for bps-domain entities.

```
bps/configio/<module>/          <- IO orchestration (bps owns)
  import_interactor.py          <- thin wrapper: creates ImportStore, calls ImportInteractor.execute()
  import_store.py               <- ImportStore subclass: 6 abstract methods + registers action_generators/handlers
  export_interactor.py          <- thin wrapper: calls service_adapter.<owning_app>_service.export_*()
  export_csv_interactor.py      <- CSV formatting only
  data_store.py                 <- RelationsDataStore (account_id, lookup maps)
  schema.py                     <- CSV sheet definitions and FK relationships
  action_generators/            <- @register_action_generator per entity type
  run_actions_handlers/         <- @register_bps_template_run_action per (entity_type, action_type)
  json_converters/              <- CSV rows -> nested JSON
  constants/                    <- CSV enums, JSON keys

<owning_app>/interactors/configio/<entity>/  <- domain logic (the app that owns the entity)
  <entity>_handler.py           <- EntityHandlerInterface implementation (run_checks_for_create/update, create, update)
  checkers/                     <- validation logic -- receives typed DTOs, never dicts
  create_*.py / update_*.py / upsert_*.py  <- domain operations
  export_interactor.py          <- actual export logic using the owning app's storages

<owning_app>/app_interfaces/service_interface.py  <- bridge (@staticmethod methods)
bps/adapters/<owning_app>_service.py              <- pass-through adapter
```

Per-entity host examples: `StageTransitionHandler` -> `sales_crm_core/`, `AccountHandler`/`TransactionHandler` -> `tdr/`, `PortalApplicationHandler` -> `portals/`, `RuleSetHandler` -> `rules_engine/`, `StageAssigneFieldLogsHandler` -> `bps/interactors/`.

## Decision Tree: Where does this file go?

- **Does it orchestrate CSV -> action -> DB?** -> `bps/configio/<module>/`
- **Does it contain domain rules, validation, or DB writes?** -> `<owning_app>/interactors/configio/<entity>/` — pick the app that owns the entity's domain
- **Does it bridge the two apps?** -> `<owning_app>/app_interfaces/service_interface.py` + `bps/adapters/<owning_app>_service.py`

## Cross-App Isolation in ConfigIO

`run_actions_handlers` in `bps/configio/<module>/` should not import from the owning app's internals directly — this breaks app isolation and makes modules untestable independently.
All cross-app calls go through `get_service_adapter().<owning_app>_service.<method>()`.

```python
# CORRECT
def execute(self, action: ChangeConfigActionDTO) -> None:
    self.sale_crm_service.create_relation_config(
        relation_config=action.entity_dto,
        data_store=self._data_store,
        account_id=self._data_store.account_id,
    )

# Wrong -- don't do this in bps/
from sales_crm_core.interactors.configio.relations.relation.relation_handler import RelationHandler
handler = RelationHandler(data_store=data_store)
handler.create(entity=action.entity_dto)
```


## Tenancy: Bind Writes to the Authorised Scope, Never to a CSV Row

### WHY
The same cross-tenant WRITE bug was found by security review in THREE consecutive configio/populate features — even after an explicit "build it in from the start" instruction. A scope id (`account_id` / `pipeline_item_template_id` / `portal_id`) read straight from a CSV row lets an import for account-A write into account-B's config (or leak which ids are valid for a foreign scope via a PUBLIC_READ remarks file). This is the highest-priority configio invariant.

### The Rule
- **The authorised scope is the import context's scope, not the CSV's.** Take the target scope id from the import context / data store (the mutation param, `data_store.account_id`, `data_store.get_bps_template_id()`), never from a `*_id` column in a row.
- **Reject or filter foreign-scope rows BEFORE any storage or adapter write.** A row whose scope id ≠ the authorised scope id must be dropped (action-generator path) or marked FAILED (populate path) before any setter, lookup, or field-ref resolution runs.
- **Fail safe on missing scope.** If the authorised scope id resolves to `None` (template/account not found), drop all rows — do not fall back to the CSV value.

### Canonical guards (the pattern, written two ways)
- Action-generator path — `_filter_to_authorised_template` in `bps/configio/bps_template/action_generators/generate_actions_for_pmu_site_fields.py` (drops rows whose `pipeline_item_template_id` ≠ `data_store.get_bps_template_id()`).
- Populate path — `build_rejected_rows_for_mismatched_template_ids` in `bps/populate/populate_bps_template_config/template_id_guard.py` (marks mismatched rows FAILED before field-ref lookup).

### Required test (non-negotiable, see testing.md)
Every configio entity that writes a scoped entity MUST have a test asserting a foreign-scope row does NOT write — `assert_not_called()` on the REAL setter/storage method — and that the guard runs before the write. A green suite without this test does not prove the guard exists.

## Data Type Conversions

- **Follow schema engine converters pattern** — for configio data type conversions, check the schema engine converter registry for existing converter classes. Create a dedicated converter class registered as a schema type rather than embedding conversion logic directly in strategy classes.
- **Match existing serialization formats** — before choosing a serialization format for export (e.g., expression strings vs structured dicts), check existing sample JSONs and converter implementations to match the established pattern.
- **Boolean CSV tokens are `YES`/`NO`, not `TRUE`/`FALSE`.** `BooleanFromSheetsEnum`'s truthy token is `"YES"`, and the SchemaEngine `"type": "boolean"` serializer emits the same `YES`/`NO` tokens — which is exactly what lets a boolean field round-trip export⇄populate on one shared CSV column with zero translation. Test trap: a populate/export boolean test using `"TRUE"` silently parses to `False` and passes as a false-green. Assert boolean columns with `"YES"`/`"NO"`.


## Canonical Reference

`StageTransitionHandler` in `sales_crm_core/interactors/configio/stage_transitions/stage_transition_handler.py` is the canonical example of an `EntityHandlerInterface` implementation. It happens to live in `sales_crm_core` because that app owns stage-transition domain logic — the location is an example of the pattern, not a rule. Handlers for entities owned by other apps live in those apps.

For the full handler contract (the 7 methods, which flow uses which, host-app rules, cross-app wiring), see `.claude/skills/configio-export-guide/references/entity-handler-interface.md`.
