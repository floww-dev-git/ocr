---
name: gateway-tests-expert
description: Write front-door gateway tests for any gateway type — GraphQL mutation/query, SQS handler, step function, scheduler tick, async event. Enters through the REAL production entry point, runs real interactors/storages/adapters against real owned stores (sqlite/moto DynamoDB/fakeredis/ES), mocks only true externals. cases.md-driven, dual-assert (response + store snapshot), parallelized via subagents. Use when the user says "write gateway tests", "gateway test for <operation>", "front-door test", "test this mutation/query/handler at the gateway", or names a gateway operation to cover end-to-end.
argument-hint: "[gateway operation — mutation/query name, handler method, or job/event name]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash, Agent
---

# Gateway Tests Expert

Write gateway tests for: $ARGUMENTS

**North star:** `common/tests/common_fixtures/README.md` — assemble the real system, drive it
through a real gateway, assert real state. The only mocks are true externals (a process
boundary we don't deploy). Read it before the first test; this skill wraps that harness,
it does not replace it.

**Canonical exemplars** (read these instead of inventing shape):
- Full package: `fee_engine/tests/gateway_tests/add_fee_headers_in_entity_fee_rule_set/`
- `cases.md` format: `fee_engine/tests/gateway_tests/add_fee_headers_in_entity_fee_rule_set/cases.md`
  (14 cases, 6 groups — the shape at a readable size).
  `sales_crm_core/tests/gateway_tests/update_application_field_in_portal/cases.md` is the same
  shape at 62 cases / 18 groups. All 60 suites carry the table-only, letter-grouped shape; a file
  showing `###` per-case sections or bare-number case ids is unconverted
- Coverage compass: `fee_engine/tests/gateway_tests/index.md`

## When to use / when NOT

| Skill | Seam | Entry point | Storage |
|---|---|---|---|
| `interactor-test-writer` | UNIT | interactor method, direct call | mocked (StorageMock, autospec) |
| `write-integration-testcase` | integration | interactor method, direct call | real DB, real storages |
| **gateway-tests-expert** (this) | **front door** | **REAL production gateway** (schema executor, SQS handler, step-fn handler, scheduler tick, async event) | real owned stores (rds/dynamo/redis/es) |

Use this skill when the test subject is a gateway OPERATION (a mutation/query name, a handler,
a job type) and the goal is end-to-end coverage through the door production uses. Use
`write-integration-testcase` when the subject is an interactor with no gateway in scope; use
`interactor-test-writer` for unit coverage of one interactor's branches.

## The harness (pointers, not copies)

| Piece | Home | Gives you |
|---|---|---|
| Gateways | `common/tests/common_fixtures/gateways.py` | `gql.run` / `gql.run_async`, `sqs.deliver`, `scheduler.tick`, `async_event.deliver`, `step_function.dispatch` |
| Stores | `common/tests/common_fixtures/stores.py` | `wire_stores` (autouse moto DynamoDB + fakeredis), `relational_db`, `elasticsearch` |
| Assert | `common/tests/common_fixtures/snapshots.py` | `snapshots.response(...)`, `snapshots.stores(rds=/dynamo=/redis=/es=, normalize=[...])` |
| Arrange | `common/tests/common_fixtures/factory_json.py` | `@register_builder`, `World`, `load_world`, the `given` fixture |
| Externals | `common/tests/common_fixtures/externals.py` | `stub_razorpay`, `stub_docusign`, `stub_aws_transport` — wire-level ONLY |
| Determinism | `common/tests/common_fixtures/__init__.py` | `seed_uuid_generation(mocker, count=...)` |
| Builders | `<owning_app>/tests/builders.py` | domain arrange builders, self-registered per app |

## Workflow

### Step 1 — Identify the operation's input and output

Name the front door precisely: the mutation/query name (gql), the handler + message shape
(sqs), the operation/event name (step function / async event), or the tick (scheduler).
Pin its INPUT (params/message/event) and OUTPUT (response union / return dict / side effects
only). Per-type identification and helper usage: `references/gateway-types.md`.

### Step 2 — Bounded discovery of the cases

Dig into the implementation behind the door: resolver → interactor → composed interactors →
storages → adapters. Map the EXECUTION FLOW and the composition, and extract every case —
big and small: happy paths, each typed error, filters/precedence, pagination, guards,
concurrency invariants, cross-app side effects. Then STOP. This is bounded discovery: the
composed interactors + flow are the map; don't spelunk every leaf. Close by cross-checking
the case list against what the code can actually do (a case the code can't reach is noise;
a reachable branch with no case is a gap).

### Step 3 — Write `cases.md` (the source of truth)

Before any test code, write `<app>/tests/gateway_tests/<operation>/cases.md`: intro +
`**Groups:**` legend + `<style>` block + **ONE table, one row per case**, columns exactly
**`| Case | Title | What it drives | builder_json | Assertions | Test |`**. Cases in INCREASING
order of complexity (smoke first → comprehensive/critical last). Follow
`references/cases-md-format.md` EXACTLY.

**Case ids are letter-grouped — `A1`, `A2`, `B1`, … — in every file, no exceptions.** The letter
names a theme, the number is the position inside it. Groups are the contiguous RUNS the
complexity order already forms (grouping never reorders rows), letters are positional and never
mnemonic, error/access groups come last, and the intro carries a
`**Groups:** A · <name> — B · <name>` legend plus a `**N cases, G groups, all covered.**` count.
Prose cites a case by its grouped id (`case C2`), never a bare number. Full rules + the WHY:
`references/cases-md-format.md` § Grouping. Verify with
`python3 .claude/scripts/check-cases-md.py <app-or-suite>`.

It must read as a record of **what each case proves**, not of intentions: what the case drives
(the world and the act, in words), the fixture file it loads, and the assertions — the
plain-English claims the test stands behind, never a copy of its `assert` statements. Assertions
are `<br>`-separated and REQUIRED.

Two rules that keep this honest:
- **`cases.md` restates no arrange data.** `factory_jsons/<case>.json` is the single source of
  truth for the world; the row names the FILE and nothing more. A mirrored copy is a second
  source of truth that goes stale on the next fixture edit.
- **Never write a name you have not read.** Every identifier comes from the fixture, the test,
  or the schema. Filling in a plausible id is the one failure this format cannot survive.

### Step 4 — Build the bed, THEN parallelize

Set up the shared per-operation bed first (single-writer — one author, no fan-out yet):

1. **Package dir** `<app>/tests/gateway_tests/<operation_name>/` — package = ONE gateway
   operation; the gateway TYPE is a column in `index.md`, never part of the folder name.
   Cross-app rule: the test's home is the app where the resolver's INTERACTOR lands.
2. **`__init__.py`** — the shared MUTATION/QUERY (or event/message shape) defined ONCE and
   imported by every test file. Build it by these rules — all four are mandatory:
   - **Expand the whole return type recursively, every time.** Select every union branch, and
     inside each branch expand every nested object/union down to its scalars. No partial
     "just the fields I need" shortcuts. Guard cycles: if a type repeats on a path, take only
     its scalar fields the second time so the expansion terminates.
   - **Alias every colliding field.** GraphQL's SameResponseShape rule rejects two fields that
     share a response name but have different types across branches (e.g. `response` is a union
     on the success type but `String!`/`Int!` on error types; a nested `value` that differs
     across a scalar-wrapper union). One un-aliased collision makes the WHOLE query invalid at
     validation. Alias each colliding field per branch as `<TypeName>_<field>` — e.g.
     `FieldResponse_response`, `GQLStringType_value`.
   - **Generate by schema introspection — never hand-edit.** Walk
     `schema.graphql_schema.mutation_type.fields["<op>"]`, render each union member as
     `... on <Type> { __typename <fields, nested expanded, collisions aliased> }`, and require
     `validate(schema, parse(query))` to return zero errors before committing. Re-run the
     generator when the schema changes; never hand-add a branch — an un-aliased collision slips
     through by hand.
   - **Executor consequence.** The full expansion usually pulls in dataloader-backed fields on
     the success branch, so tests that reach a success branch must drive `gql.run_async` under
     `@pytest.mark.django_db(transaction=True)`. Error-branch tests stay on sync `gql.run` —
     their inline fragment resolves only scalars.

   Living reference: `sales_crm_core/tests/gateway_tests/update_application_field_in_portal/__init__.py`
   — a full 81-branch union expansion with the aliasing and the run_async note in its docstring.
3. **`conftest.py`** — imports `given` + `wire_stores` (and the named store fixtures) from
   `common.tests.common_fixtures`, plus each builder module the tests need (import
   side-effect registers them). Copy the shape from
   `fee_engine/tests/gateway_tests/conftest.py`.
4. **New builders** — any entity the cases need that has no registered builder yet. Build
   these BEFORE the fan-out; multiple cases depend on them (Step 6 owns the rules).
5. **`index.md`** — create or update the app's coverage compass row for this operation in
   the same change.

Then fan out: one subagent per test case (or small group of related cases), each owning ONLY
its `factory_jsons/<case>.json`, `test_<case>.py`, and generated snapshot. Each subagent gets
the `cases.md` row (title, what it drives, builder_json, assertions), the bed paths, and the pitfalls list
below. Subagents never touch the bed files or another case's files (single-writer per file);
each runs its own test green before reporting. The orchestrator then runs the whole package,
then the FULL app gateway suite twice (pitfall 1).

### Step 5 — Arrange (do not compromise here)

One `factory_jsons/<case>.json` per case describing the WHOLE world the case needs — every
entity, cross-app included (user, pipeline item, rule sets, orders, …). The `given` fixture
loads it: `world = given("<case>.json")`; read rows back via `world.get("<ref>")` /
`world.first("<section>")`. In the test body: `@freeze_time(...)` on the class +
`seed_uuid_generation(mocker, count=5000)` first line of Arrange, so datetimes and generated
ids are deterministic and land IN the snapshot. Start/seed any non-relational store state
here too. An incomplete world that "happens to pass" is the number-one source of flaky
gateway tests — model the full world.

The JSON holds the WHOLE world; `cases.md` names only the FILE, in its `builder_json` cell. No
arrange data is ever hand-copied into markdown — the report app
(`python3 html_report_templates/gateway_test_cases_report/serve.py`) serves the repo, lists every
suite, and reads each `cases.md` and its `factory_jsons/*.json` live off disk, so the full world
renders beside the case it belongs to and cannot drift.

### Step 6 — Builders live where the model lives

For each entity the world needs, check whether a builder is already registered:
`grep -rn "@register_builder" --include=builders.py`. Exists → use it; almost-right →
PARAMETERIZE it (add an optional key, backward-compatible no-op when absent), never fork a
near-duplicate. Missing → define it in the OWNING app's `tests/builders.py` (the app that
owns the model owns its builder) with `@register_builder("<section>")`, and import that
module in the package conftest. WHY: builders are shared arrange infrastructure — a builder
parked in the consuming app's tests is invisible to the next app that needs the same entity.

### Step 7 — Act, then dual-assert, then cross-check

**Act** is ONE call to the real entry point (`gql.run(...)`, `sqs.deliver(...)`, …) — nothing
else. For gql: default to `gql.run` (sync executor, resolvers on the test's own connection);
reach for `gql.run_async` + `@pytest.mark.django_db(transaction=True)` only when the
assertion needs dataloader-backed fields resolved (details in `references/gateway-types.md`).

**Assert** proves every entry in the case row's Assertions column, and ALWAYS both halves — a gateway
test asserting only the response is incomplete. The row says the claim in words ("the record
field response in DynamoDB now holds the new value"); the test is where the concrete value is
pinned:

1. `snapshots.response(snapshot, result)` — what the door returned.
2. `snapshots.stores(snapshot, rds=[...], dynamo=[...], redis=..., es=...)` — WHOLE stores,
   every store the path touched.
3. Explicit ORM/business asserts for relationships and structural properties (linkage,
   counts, page disjointness) that snapshots can't pin.

**Cross-check closes the loop:** after the first green run, READ the generated snapshot file
and verify it evidences every assertion in the case's row — 1:1 — and that the row's
`builder_json` still names the fixture the test loads. A written snapshot is not a verification
until inspected. Only then is the case complete; fix any drift in the test or the row (they must
not disagree).

**Retrofitting an existing suite** inverts the direction: the green tests are the ground truth, so
derive each row from the test's `given(...)` fixture and its assert lines — never from memory or
from an older prose row.

## Pitfalls (each has shipped a real failure — bake them in)

1. **Snapshot order-stability.** Server-GENERATED uuids captured in a `stores` snapshot are
   SUITE-POSITION-DEPENDENT (the global uuid mock is consumed a varying number of times by
   background code) — the test passes alone, fails in the full suite. Normalize those keys
   via `snapshots.stores(normalize=["parent_id", "added_applied_fee_header_ids", ...])` —
   including id keys nested inside JSON payload columns — and prove linkage with explicit DB
   asserts (`assert child.parent_id == parent.id`) instead of raw ids. ALWAYS run the full
   app gateway suite TWICE before calling the package done.
2. **Determinism is opt-in.** `@freeze_time(...)` + `seed_uuid_generation(mocker, count=...)`
   in every test — without both, datetimes and ids can't be captured. Only a relational
   surrogate PK is auto-blanked; everything else lands in the snapshot by design.
3. **`auto_now_add` under a frozen clock.** Every row gets the SAME timestamp, which breaks
   newest-first ordering, pagination boundaries, and earlier-than detection. Give per-row
   deterministic times via a builder queryset `.update(creation_datetime=...)` (bypasses
   `auto_now_add`; no-op when the key is absent) — pattern:
   `_override_log_creation_datetime` in `fee_engine/tests/builders.py`.
4. **Dual assert is non-negotiable.** Response snapshot AND stores snapshot for every store
   the path touched. Read-only operations still snapshot the response and assert the stores
   they read from were arranged as claimed (structural asserts suffice there).
5. **Bounded discovery.** Enumerate from the composed interactors + execution flow; verify
   the final list against reachable code paths; don't over-spend walking every leaf.
6. **Builder in the correct app, parameterized not forked.** See Step 6.
7. **Snapshot cross-check.** See Step 7 — inspect the generated snapshot against the
   `cases.md` assertions before declaring the case covered.

## Completion checklist

- [ ] `cases.md` written FIRST, format per `references/cases-md-format.md` (one table, columns
      `Case | Title | What it drives | builder_json | Assertions | Test`), cases in increasing
      complexity, `**N cases, G groups, all covered.**` count accurate
- [ ] Case ids letter-grouped (`A1`, `B1`, …), groups contiguous, `**Groups:**` legend matching
      the table, no case cited by bare number — `python3 .claude/scripts/check-cases-md.py <app>`
      passes
- [ ] Every assertion maps 1:1 to a real `assert` in the test; every `builder_json` cell names a file in
      the suite's `factory_jsons/`; every Test link resolves to an existing file
- [ ] `cases.md` carries NO arrange data — the world lives only in `factory_jsons/<case>.json`
- [ ] Every identifier in `cases.md` was READ from the fixture/test/schema, not inferred
- [ ] Bed built before fan-out: package dir, shared `__init__.py` operation (fully recursively
      expanded, collisions aliased, validates clean), conftest with `wire_stores` + `given` +
      builder imports
- [ ] Every world is a complete `factory_jsons/<case>.json`; builders live in owning apps
- [ ] Every test: `@freeze_time` + `seed_uuid_generation`, one real gateway Act, dual assert
- [ ] Mocks: true externals at the wire only (`externals.py`) — zero mocks of interactors,
      storages, adapters, or app_interfaces
- [ ] Generated snapshots READ and cross-checked against `cases.md`
- [ ] `index.md` updated in the same change (operation row + status)
- [ ] Full app gateway suite run TWICE, green both times
