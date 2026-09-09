---
globs:
  - "**/*.py"
---

# Clean Architecture

## Layer Structure (per app)
```
app_name/
  interactors/        # Business logic — one class per use case
  storages/           # Data access — converts models ↔ DTOs
  storage_interfaces/ # Abstract contracts (abc.ABC + @abc.abstractmethod)
  adapters/           # External service wrappers + ServiceAdapter singleton
  models/             # Django ORM models — schema only, no logic
  dtos/               # @dataclass DTOs — pure data, no methods
  exceptions/         # Domain exceptions inheriting BaseExceptionClass
  app_interfaces/     # Public API for other apps to consume
  constants/          # Enums and configurations
  presenters/         # Response formatting
  tests/              # Test suites with factories and mocks
```

## Communication Rules
1. **DTO-Only** — no Django model instances cross layer boundaries. All data passes as `@dataclass` DTOs or primitives. This prevents ORM lazy-load side effects and enables testing without a database.
2. **Constructor Injection** — interactors receive storage interfaces via `__init__`, access services via `@property` with lazy imports:
   ```python
   class MyInteractor:
       def __init__(self, storage: StorageInterface):
           self.storage = storage

       @property
       def iam_service(self):
           return get_service_adapter().iam_service
   ```
3. **App Isolation** — apps communicate exclusively through `app_interfaces/`. Never import another app's internals (models, storages, adapters, interactors, constants, dtos). This allows independent testing and deployment of each app. Before committing, scan for cross-app imports: `from other_app.adapters`, `from other_app.storages`, `from other_app.interactors` are all violations. *(Hook-enforced: `quality-gate.sh` catches cross-app imports on every Edit/Write)*
4. **Unidirectional** — Presenters → Interactors → Storage/Adapters. No reverse dependencies.
5. **No Layer Skipping** — each layer only talks to adjacent layers.

## Storage Pattern
- Interfaces: `abc.ABC` with `@abc.abstractmethod` on every method
- Implementations: convert models to DTOs via `_prep_*_dto()` helper methods
- Method naming: `get_*`, `create_*`, `update_*`, `delete_*`, `get_*_bulk` for batch
- Return `Optional[DTO]` for single lookups, `List[DTO]` for collections

## Exception Pattern
- Inherit from `common.exceptions.BaseExceptionClass`
- Store context as attributes: `self.entity_id = entity_id`
- Raise at the point of failure, let propagate naturally
- Translate only at layer boundaries

## Interface Design
- Split fat storage interfaces when 10+ methods serve unrelated use cases
- Prefer multiple narrow mixins over one large base class

## Inter-App Communication

Two sanctioned modes — pick by **dependency direction**, checked against stability (SDP: arrows point at the more stable abstraction):

**1. Consumer-adapter (default).** A consumer app reaches a producer through the producer's `app_interfaces/` via a deferred-import adapter. Arrow: consumer → producer.
```python
@property
def interface(self):
    from other_app.app_interfaces.service_interface import ServiceInterface
    return ServiceInterface()
```

**2. Engine-defines-ports (for plugin/engine apps).** When the app is a *stable abstraction others plug into* (an engine, a mechanism), invert the direction: the engine DEFINES its port interfaces in its own app (`ports/` — interfaces only, imports zero other apps); the PRODUCER apps IMPLEMENT those ports as thin adapters living in their own codebases; composition happens at the GraphQL resolver (the codebase's native wiring — resolvers already instantiate storages). Arrows: producers → engine. This keeps the engine framework-free and dissolves would-be cycles (a future producer→engine call adds no cycle because everything already points at the engine).

**Domain purity — the engine core carries ZERO producer-domain vocabulary.** Mode 2 is import-direction AND vocabulary. The engine owns the MECHANISM (registries, base contracts, a generic per-call context, and only the boundary ports IT needs — tenancy, a command to a system it doesn't own); the DOMAIN — every criterion, strategy, effect — is a producer-owned plug-in registered into the engine's registries, reading its OWN app's storages. A domain-named class or enum value inside the engine (`ShortfallLimitGuard`, `transition_type = SHORTFALL`) IS the leak, even when imports are clean: an engine-owned guard reaching producer data through an engine-defined fact port is a halfway house, not mode 2. Test: could you rename the engine core with zero producer vocabulary and lose nothing? If a class/enum name only makes sense to one producer, it lives in that producer app, not the engine. N fact ports for N producer facts is the smell — collapse to a generic context + producer plug-ins. Canonical: `workflow_engine/docs/features/workflow-engine-consolidation/design/plugin-architecture.md` — 19 fact ports + 5 domain-named guards collapsed to 2 boundary ports + a generic context (REF-001; caught at S6 after 6 ADRs).

Before projecting packages, check direction against stability: a stable abstraction defines ports (mode 2); an app consuming stabler services writes consumer-adapters (mode 1). Defaulting an engine to consumer-adapters (`gateways/` importing producers) is the wrong arrow.

## Service Adapter Centralization
Each app has one `ServiceAdapter` class with `@property` per service and lazy imports:
```python
class ServiceAdapter:
    @property
    def iam_service(self):
        from app.adapters.iam_service import IamService
        return IamService()

def get_service_adapter() -> ServiceAdapter:
    return ServiceAdapter()
```

## App Dependency Map
```
Core:           sales_crm_core, iam, asynq
Business:       bps, automation_workflows, fee_engine, payments_engine
Integration:    plugins, portals, analytics_copilot
API:            sales_crm_graphql, ext_client_graphql, floww_cli_graphql
Supporting:     engine_variables, ib_templates, crm_scoring, scrutiny_report
Infrastructure: jobs_engine
```

## Data Flow
```
Request → sales_crm_graphql → interactor(storage, adapters) → iam
  → storage_interfaces → asynq (events) → Response
```
