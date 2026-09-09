# EntityHandler Interface (Shared Reference)

Single source of truth for the `EntityHandlerInterface` contract used by both configio export and import. Linked from `configio-export-guide` (Phase 3) and `configio-import-guide` (Phase 4.5).

## The Contract

Defined in `bps/configio/core/io_engine/entity_interface.py`. One interface, seven methods, used asymmetrically by the two flows:

| Method | Export uses | Import uses |
|---|---|---|
| `get_entity_jsons(parent_entity_ids)` | Yes | No |
| `convert_json_to_dto(json_data)` | No | Yes |
| `validate(entity)` | No | Yes |
| `run_checks_for_create(entity)` | No | Yes |
| `run_checks_for_update(entity)` | No | Yes |
| `create(entity)` | No | Yes |
| `update(entity)` | No | Yes |

If your handler only participates in one flow, the methods unused by that flow should `raise NotImplementedError()`. Do not return a fake value, and do not stub silently — the explicit raise documents the boundary.

## Where Handlers Live

**Handlers live in the app that owns the entity's domain logic.** This is NOT a fixed location — pick the app that owns the create/update/validate rules for the entity.

Verified examples in the repo:

| Handler | Owning app | File |
|---|---|---|
| `StageTransitionHandler` (canonical example) | `sales_crm_core` | `sales_crm_core/interactors/configio/stage_transitions/stage_transition_handler.py` |
| `AccountHandler`, `TransactionHandler`, `SalesAndTransferNotificationHandler` | `tdr` | `tdr/interactors/configio/*_handler.py` |
| `StageAssigneFieldLogsHandler`, `TaskTemplateStageAssigneeConfigEntityHandler` | `bps` | `bps/interactors/configio/**/_handler.py` |
| `PortalApplicationHandler` | `portals` | `portals/interactors/portal_application_io/portal_application_handler.py` |
| `RuleSetHandler` | `rules_engine` | `rules_engine/interactors/configio/rule_set.py` |
| `AssignFriendEntity` | `bps` (in configio module) | `bps/configio/pipeline/interactors/assign_a_friend/assign_friend_entity.py` |

Naming: `<Entity>Handler`. Module path within the app is the owning app's choice — `interactors/configio/<entity>/<entity>_handler.py` is common but not required.

## Cross-App Wiring

`bps/configio/<module>/` (the IO orchestrator) NEVER instantiates a handler directly. The owning app exposes the handler through its `app_interfaces/service_interface.py`, and `bps/adapters/` provides a pass-through.

```
bps/configio/<module>/run_actions_handlers/<handler>.py
  -> get_service_adapter().<owning_app>_service.<method>(...)
    -> <owning_app>/app_interfaces/service_interface.py  (@staticmethod bridge)
      -> instantiates the EntityHandler, calls create/update/etc.
```

The owning app decides the service method shape. `sales_crm_core` exposes via `sales_crm_core/app_interfaces/service_interface.py`. A TDR-owned handler exposes via `tdr/app_interfaces/...`. New entities owned by other apps publish their own service interface.

## Constructor Pattern

Handlers receive a `data_store` (in-memory lookups + `account_id`) plus any storages from the owning app. They never receive Django models.

```python
class StageTransitionHandler(EntityHandlerInterface):
    def __init__(self, data_store: Any, lead_storage: LeadStorage):
        self.data_store = data_store
        self.lead_storage = lead_storage
```

Inside methods, instantiate interactors lazily (deferred imports) to keep the handler module light and avoid circular imports.

## Method Responsibilities

- `get_entity_jsons(parent_entity_ids)` — fetch all entities for the given parents, return `{entity_id: json_dict}`. Used by export.
- `convert_json_to_dto(json_data)` — map an incoming flat JSON record (post schema validation) to the typed entity DTO consumed by checkers/create/update. Import-side.
- `validate(entity)` — DTO-level structural validation independent of action type. Import-side, called before action-specific checks.
- `run_checks_for_create(entity)` / `run_checks_for_update(entity)` — return `List[RunActionErrorDTO]`. Run business-rule validation against existing state. Pure — no DB writes.
- `create(entity)` / `update(entity)` — perform the domain write by delegating to an existing create/update interactor in the owning app. Inside `@transaction.atomic()` from `ImportInteractor.execute()`.

## Why a Single Interface for Two Flows

The same entity is both exported (read existing state) and imported (write new state). Centralizing on one handler per entity keeps the DTO shape, the JSON key conventions, and the domain rules in one place — preventing drift between what export emits and what import accepts.

## Canonical Example

`sales_crm_core/interactors/configio/stage_transitions/stage_transition_handler.py` is the canonical reference. It demonstrates:
- Constructor with `data_store` + storage
- Import-flow methods (`run_checks_for_*`, `create`, `update`, `convert_json_to_dto`) wired to checker and create/update interactors via deferred imports
- Export-flow method (`get_entity_jsons`) — note: this particular handler stubs it because its export path is handled elsewhere; not a rule, just this handler's reality
- `validate` raising `NotImplementedError` because no DTO-level structural validation is needed beyond the checkers

Use it as an example of the pattern, not as a location rule.
