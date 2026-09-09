---
name: write-integration-testcase
description: Write integration tests that exercise real database operations, real storage implementations, and real interactors. No mocks — populate dependent apps' DB models directly instead of mocking cross-app services. Only mock truly external APIs (Razorpay, S3, etc.). Use when the user says "write integration tests", "integration test for interactor", "end-to-end test", or needs tests that verify DB state changes.
argument-hint: "[interactor path, feature name, or use case]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Write Integration Tests

Write integration tests for: $ARGUMENTS

Follow @.claude/rules/clean-code.md and @.claude/rules/testing.md for general standards.

## Core Philosophy

Integration tests verify that **real components work together** against a real database.
They are the opposite of unit tests — no mocked storages, no mocked interactors, and **no mocked cross-app services**.

The key insight: instead of mocking `get_service_adapter().fee_engine`, populate the dependent app's DB models directly (e.g., create real `EntityFeeRuleSet`, `AppliedFeeHeader`, `FeeHeader` records) so the service reads from real DB.

### What to Mock

| Component | Mock? | Rationale |
|---|---|---|
| Storage implementations | NO | Use real Django ORM storages |
| Interactors | NO | Call the real entry-point method |
| Django models / DB | NO | Use `@pytest.mark.django_db` with real records |
| Model factories | NO | Use `DjangoModelFactory` to create real DB records |
| Cross-app `app_interfaces` | NO | Populate the other app's DB directly — never mock cross-app services |
| `get_service_adapter()` properties | NO | Populate dependent app's DB instead of mocking the adapter |
| External APIs (Razorpay, S3, etc.) | YES | Cannot call real external services in tests |
| Datetime (`freeze_time`) | YES | Deterministic time-dependent behavior |
| UUID generation | YES | Deterministic IDs for assertions |
| Elasticsearch / DynamoDB | YES | Not available in test DB |

**Critical distinction:** Cross-app services that read from Django DB are NOT external. Only services that call external APIs (Razorpay, S3, email, webhooks) are external. If an app_interface reads from another app's DB, create the DB records directly — do not mock.

## Structural Rules

1. **Directory**: `integration_tests/<feature_name>/` — named by feature, NOT by app (multiple apps are involved)
2. **One BEHAVIOUR per file** — "case" means behaviour, not input row. Decision rule: same Assert block, varying inputs → `@pytest.mark.parametrize` within the file (with named `pytest.param(..., id="scenario_name")`); different Assert block (different branch/side effects) → new file
3. **`common_fixtures.py`** — only truly shared utilities go here (e.g., `make_storage()`). Keep it minimal. No mocks since we don't mock cross-app services
4. **NO local mock DTOs** — import real DTOs from the source app (e.g., `fee_engine.interactors.dtos`)
5. **NO local factories** — import model factories from `<app>/tests/factories/models.py`. If a factory doesn't exist, create it in the respective app's factory file
6. **Clear AAA sections** — every test has `# Arrange`, `# Act`, `# Assert` comments
7. **Unique ID prefixes** — each test file uses unique prefixes for all IDs (e.g., `"app-hp-1"`, `"order-amm-1"`, `"frs-moce-1"`) to avoid DB collisions between tests running in parallel or in the same transaction
8. **Traceability header** — every file's docstring carries one line: `Proves: US-x / AC-n (<one-line behaviour>)`. Makes "are all ACs covered?" a grep; survives renames

## Taming the Arrange (complex interactors)

Fixture/builder/factory division of labor and the full rules: `@.claude/rules/references/fixture-doctrine.md` — load it before writing. The short form for THIS skill:

- **Arrange > ~30 lines OR shared by 2+ files → promote to a named `given_*` scenario builder** in the feature's `common_fixtures.py`, named for the world it creates (`given_two_efrs_overpaid_latest(app_id)`), returning the entity under test, with a one-line world docstring. The test body collapses to one legible Given line + Act + Assert.
- **One-axis scenario variation → a Factory Boy `trait`** in the owning app's factory (`EntityFeeRuleSetFactory(overpaid=True)` flips the correlated field cluster) — one named flag instead of five copy-pasted overrides per file.
- **Side-effect assertions go through read-model helpers — one named helper per business invariant** (`sum_oce_amount_per_fee_header_across_all_orders`), asserting the business quantity. Never raw table dumps, never `assert_called` on a real collaborator (assert observable state, not interactions — sociable tests, Fowler).
- **Property-based (hypothesis) stays OFF this seam** — per-example DB setup is unusably slow and drowns the scenario. If a pure calculator under the interactor is edge-dense (netting, rounding, slabs), recommend a hypothesis UNIT test on it in your report-back — that's the developer's band.
- **A >100-line Arrange that survives builders is a DESIGN SIGNAL** — the interactor is likely orchestrating multiple responsibilities. Flag via the Design Correction Protocol / refactoring backlog; the test is a sensor, don't absorb the pain into a bigger builder.

## Workflow

Follow these steps in exact order. Do not skip or combine steps.

### Step 1: Identify the Test Subject

1. Read the interactor or feature to test
2. Trace the full call chain: interactor -> storages -> models
3. Identify ALL apps whose DB models are read (not just the primary app)
4. Map the FK chain — what parent records must exist before child records can be created
5. Identify truly external service calls (Razorpay, S3, etc.) that need mocking
6. Test location: `integration_tests/<feature_name>/`

### Step 2: Trace the FK Chain

Integration tests require creating parent records before children. Trace the complete chain:

Example for fee data checks (fee_engine + payments_engine):
```
fee_engine:
  FeeRuleSet → FeeHeader (FK to FRS)
  FeeRuleSet → EntityFeeRuleSet (FK to FRS)
  EntityFeeRuleSet + FeeHeader → AppliedFeeHeader (FK to both)
  EntityFeeRuleSet + Order → EntityFeeRuleSetOrder (FK to EFRS, stores order_id)

payments_engine:
  Order → OrderContributedEntity (FK to Order)
  Order → RazorpayOrder (FK to Order)
  RazorpayOrder → Payment (FK to RazorpayOrder)
  RazorpayOrder + OCE → RazorpayOrderContributedEntity (FK to both)
```

Create records top-down following this chain. Every FK field must point to a real record.

### Step 3: Find or Create Factories

1. Search `<app>/tests/factories/models.py` for existing `DjangoModelFactory` classes
2. If a factory doesn't exist, **create it in the app's own factory file** (`<app>/tests/factories/models.py`)
3. Factory must handle: `SubFactory` for FKs, `LazyFunction` for JSON fields, `.value` for enum fields, `Sequence` for unique fields
4. Never define factories locally in test files

### Step 4: Set Up common_fixtures.py

Create `integration_tests/<feature_name>/common_fixtures.py` with only truly shared utilities (e.g., `make_storage()`) — skeleton in `references/integration-test-templates.md`. No mock classes, no patch helpers, no DTO factories. If a test needs to mock a truly external API (Razorpay), do it inline in that test file.

### Step 5: Establish the Case List

**As a slice's integration-suite closer (the default in-plan invocation — the slice's final sub-task):** the case set is already defined by the sub-task's `Cases:` line per the tasks-file contract — **one test per acceptance criterion of the stories the slice serves**, none skipped. Traceability is mechanical (slice → stories → ACs); read the stories, enumerate their ACs, that IS the list. No re-derivation from execution paths, no user approval gate (Gate 3 approved it).

**Ad-hoc (no tasks file / no slice context):**
1. Analyze execution paths — focus on **data-driven scenarios**
2. One test per discrepancy type / behavior
3. Present the list to the user and **wait for approval**

### Step 6: Implement Tests (One File Per Test Case)

Each test case gets its own file: `test_<scenario>.py` — full skeleton (imports, unique ID prefixes, AAA sections, factory usage) in `references/integration-test-templates.md`.

**After implementing each test file:**
1. Run: `pytest integration_tests/<feature>/test_<scenario>.py -v`
2. If it fails, fix it before proceeding
3. Move to the next test case

### Step 7: Final Verification

1. Run all tests: `pytest integration_tests/<feature>/ -v`
2. Verify no test pollution (tests pass in any order)
3. Check test isolation (each test creates its own data with unique IDs)

## Amount Domain Rules (Financial Tests)

When testing across fee_engine and payments_engine, respect the amount domains:

| Domain | Unit | Type | Example |
|---|---|---|---|
| OCE amounts, Order amounts, RazorpayOrder amounts, Payment amounts | Paise | `int` | `10000` = Rs 100 |
| AppliedFeeHeader amounts, Consolidation amounts, Reconciliation amounts | Rupees | `Decimal` | `Decimal("100.00")` |

To match: AFH `net_amount=100.0` corresponds to OCE `amount=10000` (multiply by 100).

## Quality Checklist

Before finishing, verify:
- [ ] Every test has `# Arrange`, `# Act`, `# Assert` section comments
- [ ] `@pytest.mark.django_db` on test class or every test method
- [ ] NO `create_autospec()` or `MagicMock()` for storages — real implementations only
- [ ] NO mocking of cross-app services — populate the other app's DB directly
- [ ] NO `assert_called_once_with()` — assert on return values and DB state
- [ ] NO local mock DTOs or factory definitions — all imported from source apps
- [ ] All DB records created via `DjangoModelFactory` from `<app>/tests/factories/models.py`
- [ ] One test case per file
- [ ] Unique ID prefixes per test file (e.g., `"app-hp-1"`, `"order-amm-1"`)
- [ ] FK chain respected — parent records created before children
- [ ] Amount domains correct — paise for payments_engine, rupees (Decimal) for fee_engine/consolidation
- [ ] Interactor instantiated with real storage instances
- [ ] Only truly external APIs (Razorpay, S3) are mocked
- [ ] common_fixtures.py is minimal (just `make_storage()` or similar utilities)
- [ ] Test methods under 50 lines, max 3 indentation levels
- [ ] Tests are isolated — no shared mutable state between tests
- [ ] Every file's docstring carries its `Proves: US-x / AC-n` line
- [ ] No anti-patterns: no mock of a non-external collaborator (overmocking) · no god test spanning behaviours · no snapshot-as-golden-file where named field asserts fit · no mystery-guest setup (all arrange state visible at the call site) · no assertion roulette (invariants named, e.g. `# I1: ...`)
- [ ] All tests pass: `pytest integration_tests/<feature>/ -v`
