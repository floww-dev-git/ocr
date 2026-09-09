# Fixture Doctrine — Load-on-Demand Reference

## WHY this file exists (and why it is NOT always-on)
Fixture problems are authoring-time decisions — this loads where fixtures get written (the tester
persona, `/interactor-test-writer`, `/write-integration-testcase`), costing zero always-on
context. It complements `testing.md` (which owns the StorageMock pattern, factory rules, and
conftest-for-2+-files); nothing here repeats it. Research-backed 2026-07-04 (pytest/pytest-django
docs, Factory Boy reference, GOOS/Fowler test-data patterns); local claims verified against this
repo (~5,200 fixtures, 83 conftests, 24 `common_fixtures/` dirs).

## The three-way division of labor (the core rule)

| Need | Use | Why |
|---|---|---|
| One object / DTO with sensible defaults | **Factory Boy factory** | Declarative defaults, `Sequence` uniqueness, `create_batch` |
| One mock collaborator (storage/adapter) | **pytest fixture** (autospec, in conftest or `common_fixtures/storages.py` mixin) | DI + teardown; the StorageMock pattern |
| One multi-object domain scenario ("account with 3 pipelines, 2 items each") | **named `given_*` builder function** in `common_fixtures/` | Greppable, parameterizable, visible at the call site — no god-fixtures, no cross-module leaks |

Conflating them is how Arrange blocks rot: a "fixture" that seeds a whole world is a Mystery
Guest; a factory that wires five collaborators is a builder in denial.

## Rules

1. **Reusable scaffolding = explicit imports from `common_fixtures/`; conftest.py = locality
   only** (directory-local autospec mocks, DB/session plumbing). This repo deliberately chose
   explicit-import over conftest auto-magic — no `pytest_plugins`, no pytest-factoryboy
   auto-fixtures; they reintroduce the invisibility the convention exists to avoid.
2. **Never elevate a DB-writing fixture above function scope without yield-cleanup.** The `db`
   fixture is function-scoped so per-test rollback holds; higher scope + real writes = rows
   leaking across modules = order-dependent flakes that hide until modules run together.
3. **autouse ONLY for: factory sequence resets · DB-access enablement · time control. Never to
   inject domain data** — autouse is invisible at the test's definition point; arrange-state in
   autouse hides the very step AAA exists to surface.
4. **Freeze time on the test (`@freeze_time`), never freezegun-inside-an-autouse-fixture** — it
   corrupts `--durations` and does NOT control the clock inside other fixtures. Fixture-scope
   time control → `pytest-freezer`.
5. **A re-used fixture name at another conftest level is a documented override or a bug — never
   ambient.** Nearest-scope shadowing is silent; `pytest --fixtures <path>` is the tie-breaker.
6. **Before adding any fixture: grep `common_fixtures/` + the nearest conftests for an
   equivalent. Exists → import it. Almost-right → parameterize it, don't fork it.** No tool
   catches duplicate fixtures; authoring time is the only control (mirrors clean-code's DRY scan).
7. **Every SHARED fixture gets a one-line docstring naming what it builds** — deliberate
   exception to the no-docstring default: `pytest --fixtures` is the only inventory of a
   5,200-fixture haystack, and it renders docstrings.
8. **Scenario builders are named for the world they create** (`given_two_efrs_overpaid_latest`),
   return the entity under test, and carry a one-line world description. Promote a private
   `_arrange_*` method to `common_fixtures.py` once it's shared by 2+ files or exceeds ~30 lines.
9. **Use Factory Boy's graph tools before writing loops**: `SubFactory` (parent FKs),
   `RelatedFactory` (dependents), `traits` (one named flag flips a correlated field cluster —
   the factory-level "scenario"), `@post_generation` (post-row wiring). A 15-line flat FK
   chain in a test body is usually one missing trait.
10. **Runs: `--reuse-db` locally (`--create-db` when models/migrations changed) + the canonical
    `--no-migrations`.** Before anyone proposes xdist: factory `Sequence` uniqueness must hold
    ACROSS workers (today's `reset_sequence(1)` autouse yields identical IDs per worker — a
    latent collision) and `scope="session"` means once-PER-WORKER, not once-per-suite.
11. **A frozen bundle DTO expected to grow ships its `build_stub_*` helper in the SAME change that
    introduces it — never as an emergent fix.** When a `frozen=True` "provider/context bundle"
    (a dataclass of collaborator ports, e.g. `GuardFactProvider`) is designed to gain one field
    per later unit of work in the same slice, every test that constructs it directly breaks on
    each field addition. Front-load a `build_stub_<bundle>(**overrides)` builder with
    `create_autospec(...)` defaults for every field, so a new field costs one default here, not a
    cascade across every call site. Rule of thumb: if the ADR/task-breakdown says "N tasks each
    add a port to this bundle", the builder is part of task 1's ✔, not task N's cleanup. *(REF-001
    S2: `GuardFactProvider` grew 10 times; the early guards paid the cascade until
    `build_stub_guard_fact_provider` was added mid-battery.)*
