# Cross-Schema Imports

When cloning from `sales_crm_graphql` to `floww_cli_graphql`, every import in a cloned file falls into one of three buckets: **REWRITE** (self-referential to the destination), **CLONE** (anything that originates in the `sales_crm_graphql` schema package), or **REUSE** (shared infrastructure or cross-app domain code). Getting the third bucket wrong is what bit prior implementations — GraphQL types, DataLoaders, and utility functions were left as cross-schema imports, coupling the two schemas and creating schema-build collisions.

## Isolation principle (Article 1)

**ZERO `sales_crm_graphql.*` imports anywhere in `floww_cli_graphql/`.** Every GraphQL type, DataLoader, util, converter, factory, and resolver function originating in `sales_crm_graphql` gets cloned into `floww_cli_graphql`. Only `graphql_service.*` (schema-agnostic infra), `common.*`, and cross-app domain code (`iam.*`, `bps.*`, `sales_crm_core.*`, `automation_workflows.*`, `plugins.*`, `jobs_engine.*`, etc.) are reused.

The trade-off is explicit: we accept duplicate definitions in exchange for schema independence — changes in `sales_crm_graphql` cannot break `floww_cli_graphql`.

## Classification table

| Source path | Action |
|---|---|
| `sales_crm_graphql.<anything>.types.*` (ObjectType, InputType, Union, Enum, Interface) | **CLONE** to `floww_cli_graphql/<destination_domain>/types/` |
| `sales_crm_graphql.common_types.*` (e.g., `BaseUser`, `BasePipeline`, `Pagination`, `FileUploaderUrlResponse`) | **CLONE** to `floww_cli_graphql/common_types/` (bootstrap module if missing) |
| `sales_crm_graphql.common_error_types.*` (e.g., `UserIsNotAnAdministrator`, `InvalidLimit`, `InvalidOffset`, `PaginationLimitExceeded`) | **CLONE** to `floww_cli_graphql/common_error_types/` (bootstrap if missing) |
| `sales_crm_graphql.core_common_types.*`, `default_types.*`, `result_types.*` | **CLONE** to the parallel `floww_cli_graphql/` module (bootstrap if missing) |
| `sales_crm_graphql.enums.*` / `sales_crm_graphql.gql_enums.*` | **CLONE** to `floww_cli_graphql/enums/` |
| `sales_crm_graphql.<domain>.dataloaders.*` | **CLONE** — DataLoaders LIVE in `sales_crm_graphql`; they cannot be reused without violating Article 1 |
| `sales_crm_graphql.<domain>.utils.*` (DTO -> GQL converters, type factories) | **CLONE** to `floww_cli_graphql/<destination_domain>/utils/` |
| `sales_crm_graphql.<domain>.resolvers.*` (resolver functions used inline) | **CLONE** or **INLINE** at the call site |
| Self-referential `sales_crm_graphql.<domain>.X` where `X` is in the clone manifest | **REWRITE** to `floww_cli_graphql.<destination_domain>.X` |
| `graphql_service.custom_scalars.*` (e.g., `GQLDateTimeScalar`, `GQLRequiredList`) | **REUSE** — schema-agnostic infra |
| `graphql_service.utils.base_error_type.GraphQLBaseError` | **REUSE** — interface, not a concrete type |
| `graphql_service.dataloaders.BaseDataLoader` | **REUSE** — base class for DataLoaders |
| `graphql_service.middlewares.*`, `graphql_service.context.*` | **REUSE** — schema-agnostic |
| `common.*` (e.g., `common.exceptions.BaseExceptionClass`) | **REUSE** — cross-cutting utilities |
| `<owning_app>.interactors.*` (lazy-imported in resolver body) | **REUSE** — business logic shared by design |
| `<owning_app>.storages.*` / `<owning_app>.storage_interfaces.*` | **REUSE** — data access shared |
| `<owning_app>.adapters.*` | **REUSE** — adapters wrap external services |
| `<owning_app>.dtos.*` | **REUSE** — pure data, no GraphQL coupling |
| `<owning_app>.exceptions.*` | **REUSE** — domain exceptions caught in resolvers |
| `<owning_app>.app_interfaces.*` (e.g., `iam.app_interfaces.*`) | **REUSE** — public app API |
| `<owning_app>.constants.*` | **REUSE** — constants/enums are domain |

`<owning_app>` is any of the cross-app domain packages: `iam`, `bps`, `sales_crm_core`, `automation_workflows`, `plugins`, `jobs_engine`, `fee_engine`, `payments_engine`, etc. — anything outside `sales_crm_graphql` and `floww_cli_graphql`.

## Check before clone (Article 3)

Before adding a symbol to the clone manifest, search `floww_cli_graphql/` for an existing copy:

```bash
grep -rln "class <SymbolName>\|def <symbol_name>" \
  floww_cli_graphql/common_types/ \
  floww_cli_graphql/common_error_types/ \
  floww_cli_graphql/enums/
```

If found -> import from the local path. If absent -> add to clone manifest. Two Python classes with the same Graphene type name cause schema registration conflicts; this check prevents the trap.

## Rule of thumb (when the table doesn't list the path)

For any path inside `sales_crm_graphql.*` not in the table: **CLONE.** Article 1 is absolute — nothing from `sales_crm_graphql` may be imported by `floww_cli_graphql`.

For any path outside `sales_crm_graphql.*`: open the imported name and check its definition.

- Inside `graphql_service.*` -> **REUSE**
- Inside `common.*` -> **REUSE**
- Inside a domain app (`iam`, `bps`, `sales_crm_core`, `jobs_engine`, etc.) -> **REUSE**

The schema regeneration step (Article 6, gate B) and the schema build smoke test (gate C) fail loudly on duplicate type registration — that is the cheap signal that you cloned a symbol Article 3 should have caught.

## Rewrite mechanics (when imports point at modules in the clone manifest)

```python
# Before (in source file)
from sales_crm_graphql.jobs_engine.types import JobExecutionType
from sales_crm_graphql.jobs_engine.mappers import _to_job_execution_type

# After (in cloned file)
from floww_cli_graphql.jobs.types import JobExecutionType
from floww_cli_graphql.jobs.mappers import _to_job_execution_type
```

Only rewrite when the target module is one of the files being cloned. Imports pointing at modules NOT in the clone scope fall into the **CLONE** or **REUSE** buckets above.

## Anti-patterns

- **Any `from sales_crm_graphql ...` or `import sales_crm_graphql ...` line in a `floww_cli_graphql` file** — direct violation of Article 1.
- **Cloning an interactor / storage / DTO / exception / scalar / `GraphQLBaseError` "to be safe"** — these are explicitly shared and create divergent codepaths for the same business logic if cloned.
- **Re-cloning a shared type already present in `floww_cli_graphql/common_types/`, `common_error_types/`, or `enums/`** — produces a schema-build collision (two Python classes registering the same GraphQL type name). Run the Article 3 search first.

If you find yourself adding `from sales_crm_graphql.` to a cloned file, you are violating Article 1. Re-read the classification table.

See `floww_cli_common_modules.md` for how to bootstrap `floww_cli_graphql/common_types/`, `common_error_types/`, and `enums/` the first time a clone needs them.
