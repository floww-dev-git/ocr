# floww_cli_graphql Shared Modules

The destination schema needs its own shared modules — mirroring `sales_crm_graphql.common_types`, `common_error_types`, and `enums` / `gql_enums` — so that cloned operations have a local home for shared types, error types, and enums. These modules do not exist by default; the first clone that needs them creates them.

## Modules

| Module | Mirrors | Holds |
|---|---|---|
| `floww_cli_graphql/common_types/` | `sales_crm_graphql.common_types` | Shared GraphQL ObjectTypes used by multiple destination subfolders (`BasePipeline`, `BaseUser`, `Pagination`, `FileUploaderUrlResponse`, etc.) |
| `floww_cli_graphql/common_error_types/` | `sales_crm_graphql.common_error_types` | Shared GraphQL error types used by multiple destination subfolders (`UserIsNotAnAdministrator`, `InvalidLimit`, `InvalidOffset`, `PaginationLimitExceeded`, etc.) |
| `floww_cli_graphql/enums/` | `sales_crm_graphql.enums` / `sales_crm_graphql.gql_enums` | Shared GraphQL enums (`GQLSalesEntityType`, etc.) |
| `floww_cli_graphql/common_types/dataloaders/` | (cross-cutting DataLoaders) | DataLoaders used by multiple destination subfolders. Per Article 1, DataLoaders cannot be reused from `sales_crm_graphql`. |
| `floww_cli_graphql/common_types/utils/` | (cross-cutting utils) | Shared util / converter / factory functions used by multiple destination subfolders. |

All five are part of the CLI schema package — every class or function inside originated in `sales_crm_graphql` and was cloned per Article 1. They follow the isolation rule from `cross-schema-imports.md`: never import them from `sales_crm_graphql`.

## Bootstrap procedure

The first time a clone manifest needs a shared symbol:

1. **Run the Article 3 search first** — confirm the symbol is not already present:

   ```bash
   grep -rln "class <SymbolName>\|def <symbol_name>" \
     floww_cli_graphql/common_types/ \
     floww_cli_graphql/common_error_types/ \
     floww_cli_graphql/enums/
   ```

   If found -> import from the local path. Skip the rest of this procedure.

2. Check whether the destination module exists: `ls floww_cli_graphql/common_types/ floww_cli_graphql/common_error_types/ floww_cli_graphql/enums/`.
3. If absent, create the directory plus an empty `__init__.py`. Prefer the package form (`common_types/__init__.py` + per-type files) over a single flat module, so subsequent clones append without churn.
4. Clone ONLY the symbols your manifest references — not the entire source file. Apply the transitive closure to those symbols (a `BasePipeline` clone may pull in nested types like `BasePipelineConfig` that must also be cloned).
5. Apply the REWRITE / CLONE / REUSE classification (see `cross-schema-imports.md`) to every import inside the cloned symbols.

## Subsequent clones

Once `floww_cli_graphql/common_types/<thing>.py` exists, later clones that reference the same shared type **import from the local module**, not from `sales_crm_graphql`:

```python
# Right
from floww_cli_graphql.common_types.base_pipeline import BasePipeline

# Wrong — violates isolation rule
from sales_crm_graphql.common_types import BasePipeline
```

If a later clone needs a NEW shared type that hasn't been cloned yet, add it to the local module the same way — clone the type definition, apply the transitive closure, classify imports.

## Layout suggestion

A flat single-file mirror works for small schemas, but grows hard to navigate once 6+ shared types accumulate. Prefer the package layout from the start:

```
floww_cli_graphql/
  common_types/
    __init__.py          # re-exports for `from floww_cli_graphql.common_types import X`
    base_pipeline.py
    base_user.py
    pagination.py
    file_uploader_url_response.py
    dataloaders/
      __init__.py
      <shared_dataloader>.py
    utils/
      __init__.py
      <shared_util>.py
  common_error_types/
    __init__.py          # re-exports
    user_is_not_an_administrator.py
    invalid_limit.py
    invalid_offset.py
    pagination_limit_exceeded.py
  enums/
    __init__.py          # re-exports
    gql_sales_entity_type.py
```

`__init__.py` re-exports so call sites can write `from floww_cli_graphql.common_types import BasePipeline` instead of `from floww_cli_graphql.common_types.base_pipeline import BasePipeline`. This keeps cloned resolver code visually close to the source.

## Manifest reporting

When a clone adds new types to either module, surface that in the Step 3 manifest:

```
Shared modules updated:
  floww_cli_graphql/common_types/        (NEW MODULE - bootstrapped)
    + BasePipeline (cloned from sales_crm_graphql.common_types)
    + BaseUser     (cloned from sales_crm_graphql.common_types)
  floww_cli_graphql/common_error_types/  (existed)
    + PaginationLimitExceeded (cloned from sales_crm_graphql.common_error_types)
```

The operator should see at a glance which shared types travelled with this clone, so they can spot accidental over-cloning before the gate.

## Anti-patterns

- **Re-exporting symbols from `sales_crm_graphql.*` through `floww_cli_graphql/common_types/`** — a thin wrapper around the coupling Article 1 forbids. CLONE the definition itself.
- **Cloning the entire `sales_crm_graphql/common_types.py` file as one block** — the source file holds many unrelated types. Clone only what your manifest needs; future clones add more.
- **Letting two destination subfolders each clone their own copy of the same shared type** — produces a schema-build collision (two Python classes registering the same Graphene type name). The shared module exists to prevent exactly this. Run the Article 3 search every time.
