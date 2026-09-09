# Transitive Closure Checklist

The job of Step 2 in the skill is to enumerate every artifact that travels with the cloned operation. Missing an item here is the #1 cause of broken clones — every prior bug was a missed field, missed resolver, missed helper, or a `sales_crm_graphql.*` import that should have been cloned but was left as a cross-schema reference.

Process this checklist file-by-file, line-by-line. Do NOT summarize. Do NOT eyeball.

## Algorithm (Article 5)

The closure expands recursively until it reaches a fixed point. Build the full manifest BEFORE writing any files.

1. Start at the operation's return type — success ObjectType + every error type in the response Union.
2. For each ObjectType: enumerate every field, every `resolve_*` method, every helper called inside resolvers.
3. For each field whose type is another ObjectType / Union / Interface: **recurse**.
4. For each Union: add ALL declared members (Article 4 — never drop members).
5. For each `resolve_*` method: if it uses a DataLoader, add the DataLoader to the manifest (DataLoaders are CLONE, not REUSE).
6. For each helper called: if it's a DTO -> GQL converter or type factory, add it.
7. For each error type the resolver can `raise` or `return`: add it.
8. **Stop conditions**: scalars, `graphql_service.*` infra, `common.*`, cross-app domain imports (REUSE), and items already present in `floww_cli_graphql/common_types/` / `common_error_types/` / `enums/` (Article 3 — search before adding).
9. Present the manifest -> wait for `yes` -> then write files.

## Per operation

For each operation name supplied as input:

1. Locate the resolver file or mutation class file under `sales_crm_graphql/<domain>/`.
2. Locate the registration site (`graphene.Field(...)` on the `*Queries` class, or the mutation class on the `*Mutations` class).
3. Identify the **params class** (input type).
4. Identify the **response Union** and every member of it (success + every error type).

## Per type (recursive)

For each type discovered above, open the file and enumerate by reading line-by-line:

### ObjectType
- [ ] Every declared field — write down the name and graphene type of each one.
- [ ] Every `resolve_<field>` method on the class — these back computed fields and are easy to miss because they sit below the field declarations.
- [ ] Every other type referenced via `graphene.Field(OtherType)`, `graphene.List(of_type=OtherType)`, or `GQLRequiredList(OtherType)`. Recurse into each.
- [ ] Any `class Meta:` with `interfaces = (...)` — interface types are part of the closure.

### InputObjectType
- [ ] Every declared field, including nested input types. Recurse into nested inputs.

### Union (response types)
- [ ] Every type listed in `class Meta: types = (...)`. Each is in the closure — success type + every error type.

### Error type
- [ ] Every contextual field (`entity_id`, `job_type`, etc.) — must match the corresponding domain exception's attributes.
- [ ] The interface it implements (typically `GraphQLBaseError` from `graphql_service.utils.base_error_type`).

## Recursive clone-traversal for `sales_crm_graphql.*` imports

After enumerating types directly referenced by the operation, walk every `sales_crm_graphql.*` import in every cloned file and add the target to the clone list. This step is recursive: a cloned symbol's own dependencies may pull in more `sales_crm_graphql.*` symbols that must also be cloned.

For every cloned source file, scan its imports and apply the classification table in `cross-schema-imports.md`:

- **GraphQL types (`graphene.ObjectType` / `InputObjectType` / `Union` / `Enum` / `Interface`) from `sales_crm_graphql.*`** -> CLONE. Open the source file and recurse.
- **Shared GraphQL types from `sales_crm_graphql.common_types`, `common_error_types`, `core_common_types`, `default_types`, `result_types`, `enums`, `gql_enums`** -> CLONE to the corresponding `floww_cli_graphql/` shared module (see `floww_cli_common_modules.md`). Run the Article 3 search FIRST — if already present, import locally instead of re-cloning.
- **DataLoaders (`sales_crm_graphql.<domain>.dataloaders.*`)** -> CLONE. DataLoaders live in `sales_crm_graphql` and cannot be reused (Article 1).
- **Utils / converters / factories (`sales_crm_graphql.<domain>.utils.*`)** -> CLONE to `floww_cli_graphql/<destination_domain>/utils/`.
- **Inline resolvers (`sales_crm_graphql.<domain>.resolvers.*`)** -> CLONE or INLINE at the call site.
- **`graphql_service.*`, `common.*`, cross-app domain (`iam.*`, `bps.*`, `sales_crm_core.*`, `jobs_engine.*`, etc.)** -> REUSE, preserved untouched.

Repeat until the clone manifest reaches a fixed point — no newly added symbol pulls in another `sales_crm_graphql.*` import that is not already on the list.

### Worked example — recursive clone of a shared type

Cloning `getPortalPipelines` (returns `Portal` which has `portal_pipelines = GQLRequiredList(BasePipeline)`):

1. `Portal` is in `sales_crm_graphql/configuration/portals/types/types.py` -> add to clone manifest.
2. `Portal.portal_pipelines` references `BasePipeline` (imported from `sales_crm_graphql.common_types`) -> add `BasePipeline` to clone manifest, destination `floww_cli_graphql/common_types/base_pipeline.py`.
3. Open `BasePipeline`'s definition. Its fields reference `BasePipelineConfig`, `GQLPipelineType`, `BaseUser` (all from `sales_crm_graphql.common_types` or `sales_crm_graphql.gql_enums`) -> add each to the clone manifest under the relevant `floww_cli_graphql/common_types/` or `floww_cli_graphql/gql_enums/` location.
4. Open each of those. Continue until no new shared GraphQL types appear.

The final manifest lists `Portal` + every shared GraphQL type reachable through its fields, with their destination paths.

## Per resolver / mapper

For each resolver function and each `_to_*_type` mapper in the closure:

- [ ] Every `from .X import Y` and `from sales_crm_graphql.<self_domain>.X import Y` where `X` is in the clone manifest -> rewrite to `floww_cli_graphql.<destination_domain>.X`.
- [ ] Every `sales_crm_graphql.*` import (GraphQL types, DataLoaders, utils, factories, inline resolvers) -> classify per `cross-schema-imports.md` and add to the clone manifest. Per Article 1, NOTHING from `sales_crm_graphql` survives in `floww_cli_graphql/`.
- [ ] Every REUSE-category import (`graphql_service.*`, `common.*`, cross-app domain like `iam.*`, `bps.*`, `jobs_engine.*`, interactors, storages, DTOs, exceptions, scalars, interfaces) -> preserved untouched.
- [ ] Every helper function called from the resolver body. Open each helper and recurse — helpers can call other helpers.
- [ ] Every interactor / storage / adapter class instantiated inside the resolver. These imports stay as-is (resolvers call the same backend on both schemas).

### Worked example — DataLoader and type both clone

`Portal.resolve_portal_pipelines` body:

```python
@staticmethod
def resolve_portal_pipelines(root, info):
    from sales_crm_graphql.configuration.portals.dataloaders.portal_pipelines import (
        PortalPipelinesDataLoader,
    )
    loader = PortalPipelinesDataLoader(context=info.context)
    return loader.load(key=root.portal_id)
```

When cloning `Portal` into `floww_cli_graphql/portals/types/types.py`:
- `PortalPipelinesDataLoader` is a DataLoader living in `sales_crm_graphql` -> **CLONE** to `floww_cli_graphql/portals/dataloaders/portal_pipelines.py`. The resolver's lazy import rewrites to `from floww_cli_graphql.portals.dataloaders.portal_pipelines import PortalPipelinesDataLoader`. DataLoaders are part of the schema package; Article 1 forbids importing them across schemas.
- `BasePipeline` (the element type of the field this resolver backs) is a shared GraphQL type. Run the Article 3 search first — if absent, **CLONE** to `floww_cli_graphql/common_types/base_pipeline.py`. If already present, import locally.

The resolver body's logic is identical to the source; only the two imports change. The field declaration at the class level imports the cloned `BasePipeline` from `floww_cli_graphql.common_types`.

## Per helper

For each helper function called from a resolver or mapper:

- [ ] Its full source — clone byte-for-byte.
- [ ] Every helper it calls in turn — recurse.
- [ ] Every constant / enum / module-level name it references from the same file — include in the clone scope (or reuse-list if it's a shared infra constant).

## Co-located out-of-scope types

Source files in `sales_crm_graphql/<domain>/types/` (especially `types.py`) often contain MANY types — some referenced by the operations being cloned, some referenced only by other operations that are NOT in scope. Decide what to do per source file:

1. Clone the entire file as-is to preserve relative ordering, shared imports, and module-level helpers.
2. After cloning, list classes used **exclusively** by out-of-scope operations (i.e., classes that do NOT appear in your manifest's "Types to clone" table).
3. Delete those out-of-scope classes from the destination file.
4. Run `grep` for each deleted class name across `floww_cli_graphql/<destination_domain>/` to confirm no dangling references.
5. Re-verify imports — remove any import line introduced solely for a now-deleted class.

### Worked example

Smoke test cloned `getUserAppConfig` from `sales_crm_graphql/user/types/user_app_config_types.py`. The file also defined `UserAppConfigForAdmin`, used only by `getUserAppConfigForAdmin` (out of scope).

- Cloned the full file to `floww_cli_graphql/user/types/user_app_config_types.py`.
- Deleted the `UserAppConfigForAdmin` class block.
- `grep -r "UserAppConfigForAdmin" floww_cli_graphql/user/` returned no hits.
- Removed the now-unused `AdminRoleEnum` import that only `UserAppConfigForAdmin` referenced.

Apply the same procedure whenever a source file is partially in scope.

## Final tally

Before presenting the clone manifest, you should have:
- N operation entries (queries + mutations).
- M ObjectType / Union / InputObjectType entries in domain subfolders.
- S shared GraphQL type entries destined for `floww_cli_graphql/common_types/`, `common_error_types/`, `enums/`, `core_common_types/`, `default_types.py`, `result_types/`.
- L DataLoader entries destined for `floww_cli_graphql/<destination_domain>/dataloaders/` (or `common_types/dataloaders/` if shared).
- U util / converter / factory entries destined for `floww_cli_graphql/<destination_domain>/utils/` (or `common_types/utils/` if shared).
- K helper function entries (private `_helper`, module-level constants, etc.).
- A list of self-referential imports (will be rewritten).
- A list of REUSE imports (`graphql_service.*`, `common.*`, cross-app domain — preserved as-is).
- A list of "already present in `floww_cli_graphql/`" entries (per Article 3 search — these import locally, no clone needed).
- For each partially-in-scope source file: a list of co-located classes to delete after the file is cloned.

If any field, method, or helper in a cloned file references a name that is NOT in one of those lists, the closure is incomplete — go back and add it. If any cloned file still has a `from sales_crm_graphql` or `import sales_crm_graphql` line, Article 1 is violated — promote that symbol to the clone manifest.
