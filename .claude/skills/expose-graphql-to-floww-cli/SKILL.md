---
name: expose-graphql-to-floww-cli
description: Strict-mirror clone of one or more GraphQL queries/mutations from `sales_crm_graphql` to `floww_cli_graphql`. Use when the user says "expose to floww cli", "mirror to floww cli graphql", "clone graphql to cli", "port query to floww cli", or names an operation to re-publish on the CLI endpoint.
argument-hint: "[operation_name ...] [--rename old=new] [--destination-domain <subfolder>]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Expose GraphQL to Floww CLI

Clone existing GraphQL operations from `sales_crm_graphql` into `floww_cli_graphql` with byte-level fidelity on resolver logic. The CLI schema is a derivative of the main schema — same observable shape, same backend interactors — but the two schemas are **independent at the GraphQL layer**.

Follow @.claude/rules/graphql.md and @.claude/rules/clean-architecture.md

## Article 1 — Strict isolation (the rule that drives everything else)

**ZERO `sales_crm_graphql.*` imports anywhere in `floww_cli_graphql/`.** This applies to:

- GraphQL types (`ObjectType`, `InputObjectType`, `Union`, `Enum`, `Interface`)
- Shared error types (`common_error_types.*`)
- DataLoaders (they live in `sales_crm_graphql.<domain>.dataloaders.*` — clone them, do not import)
- Utility / converter functions (`<domain>.utils.*`, DTO -> GQL converters, type factories)
- Resolver functions used inline

What IS preserved as-is (REUSE — these are schema-agnostic infrastructure or cross-app domain): `graphql_service.*` (scalars, `GraphQLBaseError`, `BaseDataLoader`, middlewares, context), `common.*`, and every cross-app domain import (`iam.*`, `bps.*`, `sales_crm_core.*`, `automation_workflows.*`, `plugins.*`, `jobs_engine.interactors.*`, etc.).

**The trade-off is explicit:** schema independence > deduplication. `sales_crm_graphql` changes must never break `floww_cli_graphql`. Duplicate type definitions are the price.

## Article 2 — Classification (CLONE vs REUSE)

| Source path | Action |
|---|---|
| `sales_crm_graphql.<anything>.types.*` (ObjectType, InputType, Union, Enum, Interface) | **CLONE** |
| `sales_crm_graphql.common_types.*`, `common_error_types.*`, `core_common_types.*`, `default_types.*`, `result_types.*` | **CLONE** |
| `sales_crm_graphql.<domain>.dataloaders.*` (DataLoaders LIVE in sales_crm_graphql) | **CLONE** |
| `sales_crm_graphql.<domain>.utils.*` (DTO -> GQL converters, type factories) | **CLONE** |
| `sales_crm_graphql.<domain>.resolvers.*` (resolver functions used inline) | **CLONE** or **INLINE** |
| `sales_crm_graphql.enums.*`, `sales_crm_graphql.gql_enums.*` | **CLONE** |
| `graphql_service.*` (custom_scalars, base_error_type, dataloaders base, middlewares, context) | **REUSE** — shared infra |
| `common.*`, `iam.*`, `bps.*`, `sales_crm_core.*`, `automation_workflows.*`, `plugins.*`, etc. | **REUSE** — cross-app domain, not source schema |

Full rationale and the rule-of-thumb fallback for unlisted paths: `references/cross-schema-imports.md`.

## Article 3 — Check before clone (the duplicate-class trap)

Before cloning a type, util, DataLoader, or enum, **search `floww_cli_graphql/` first**. If the symbol already exists in a shared destination module, import locally — DO NOT re-clone.

Two Python classes with the same Graphene type name cause schema registration conflicts. We hit this twice in prior sessions — once for a common type, once for an enum. Search every time.

Destinations to search:

- `floww_cli_graphql/common_types/` — shared GraphQL types
- `floww_cli_graphql/common_error_types/` — shared error types
- `floww_cli_graphql/enums/` — shared enums
- `floww_cli_graphql/common_types/dataloaders/` — shared DataLoaders
- `floww_cli_graphql/common_types/utils/` — shared utility functions

Search procedure:

```bash
grep -rln "class <SymbolName>\|def <symbol_name>" \
  floww_cli_graphql/common_types/ \
  floww_cli_graphql/common_error_types/ \
  floww_cli_graphql/enums/
```

If found -> import from that path. If not found -> add to clone manifest.

## Article 4 — Unions: clone ALL members + factory MUST stay in the same file

Large Union types (`Field` with 20 members, `Node` with 26, `Trigger` with ~10, `Stage family` with 25 interlinked types, `Layout/BaseTab` with 34 implementors) require two structural guarantees:

1. **Clone every Union member faithfully.** Scope is conservative — never drop members "we don't think the CLI needs". The schema must enumerate the same union members as the source.
2. **The factory function MUST live in the same file as the Union declaration.** Examples: `get_node_types()`, `get_trigger_types()`, `get_field_configuration_graphql_types()`. Splitting members across files OR moving the factory elsewhere breaks Graphene's internal registration.

This is a hard structural constraint, not a stylistic preference.

## Article 5 — Transitive closure algorithm

The closure expands recursively. Build the full manifest BEFORE writing any files. Present to the user for confirmation at the gate.

1. Start at the operation's return type — success ObjectType + every error type in the response Union.
2. For each ObjectType: enumerate every field, every `resolve_*` method, every helper called inside resolvers.
3. For each field whose type is another ObjectType / Union / Interface: **recurse**.
4. For each Union: add ALL declared members.
5. For each `resolve_*` method: if it uses a DataLoader, add the DataLoader to the manifest.
6. For each helper called: if it's a DTO -> GQL converter or type factory, add it.
7. For each error type the resolver can `raise` or `return`: add it.
8. **Stop conditions**: scalars, `graphql_service.*` infra, cross-app domain imports (REUSE), and items already present in `floww_cli_graphql/common_types/` / `common_error_types/` / `enums/` (per Article 3).
9. Build the manifest -> present to user -> proceed only after `yes`.

Exhaustive per-type / per-resolver / per-helper procedure + worked examples: `references/transitive-closure-checklist.md`.

## Article 6 — Final verification (three mandatory gates)

Before declaring done, all three must pass:

**A. Strict-isolation grep**

```bash
grep -rn "^\s*from sales_crm_graphql\|^\s*import sales_crm_graphql" \
  floww_cli_graphql/ --include="*.py"
```

Must return ZERO actual import statements. Docstring / comment mentions of `sales_crm_graphql` are acceptable (a sentence in a docstring is not an import).

**B. Schema regeneration**

```bash
python manage.py schema_gen --schema floww_cli_graphql.schema.schema \
  --out floww_cli_schema --schema_enum FLOWW_CLI_SCHEMA
```

Must succeed. Stage both `floww_cli_schema.graphql` and `floww_cli_schema_path_map.py`.

**C. Schema build smoke test**

```bash
python -c "from floww_cli_graphql.schema import schema; print(len(schema.get_type_map()))"
```

Must print a number, not error. Catches Graphene type-name conflicts that schema_gen sometimes lets through.

## Workflow

1. **Discover sources** — for each operation name, use Grep/Glob (never assume) to locate the resolver/mutation file, the registration site on `*Queries` / `*Mutations`, the input params class, and the response Union + members.
2. **Build transitive closure** — apply Article 5. Run the Article 3 search for every candidate symbol to avoid re-cloning shared types/enums/DataLoaders.
3. **Single confirmation gate** — present one manifest (operations, domain types, resolver methods, helpers/converters/factories, DataLoaders, input types, error types, shared-module updates, "already present" entries, REUSE imports preserved, schema wiring). Wait for `yes`. After approval, execute Steps 4-6 without further questions per @.claude/rules/consent-granularity.md.
4. **Clone files** — rewrite self-referential imports to `floww_cli_graphql.*`; replace cross-schema imports with the cloned local destination (or the local path discovered via Article 3); preserve REUSE imports untouched; apply `--rename` flags to operation names, class names, and `resolve_*` function names only.
5. **Wire into schema.py** — add the query field to the relevant `*Queries(graphene.ObjectType)` class (create if `--destination-domain` is new); add the mutation class to `*Mutations`; if a new `*Queries` / `*Mutations` class is introduced, append it to `QUERY_CLASSES` / `MUTATION_CLASSES` in `floww_cli_graphql/schema.py`.
6. **Run Article 6 verification** — all three gates (A isolation grep, B schema regen, C smoke test) must pass. Stage regenerated schema files.

No new tests required by default. Resolver logic is unchanged, so existing source-side tests cover the backend behavior. Scaffold destination-side smoke tests only if explicitly asked.

## Authority boundaries

- MAY create files under `floww_cli_graphql/<destination_domain>/{resolvers,mutations,types,dataloaders,utils}/`.
- MAY create and append to `floww_cli_graphql/common_types/`, `floww_cli_graphql/common_error_types/`, `floww_cli_graphql/enums/` (shared destination modules — see `references/floww_cli_common_modules.md`).
- MAY append to `floww_cli_graphql/<destination_domain>/queries.py`, `mutations/__init__.py`, and `floww_cli_graphql/schema.py`.
- MAY regenerate `floww_cli_schema.graphql` and `floww_cli_schema_path_map.py`.
- MUST NOT modify `sales_crm_graphql` source files.
- MUST NOT hand-edit `floww_cli_schema.graphql` — regenerate.
- MUST NOT leave any `from sales_crm_graphql` or `import sales_crm_graphql` line in `floww_cli_graphql/` (Article 1).

## References

- `references/cross-schema-imports.md` — full CLONE / REUSE classification table + rule-of-thumb fallback for unlisted paths.
- `references/transitive-closure-checklist.md` — exhaustive enumeration procedure for Article 5, including recursive shared-type traversal.
- `references/floww_cli_common_modules.md` — layout and bootstrap procedure for `floww_cli_graphql/common_types/`, `common_error_types/`, `enums/`.
