---
globs:
  - "**/tests/**"
  - "**/test_*.py"
  - "integration_tests/**"
  - "conftest.py"
---

# Testing Rules

## Framework
- **pytest** as primary framework, **Factory Boy** for test data generation
- Run: `pytest <path> --no-migrations -v`

## Test Structure
- Test file: `<app>/tests/interactors/<sub_module>/test_<interactor_name>.py`
- Test class: `Test<InteractorName>` inheriting `StorageMock`
- Test method: `test_<scenario_description>` — descriptive, no abbreviations
- **Error cases first**, success cases last
- Use `@freeze_time("2020-01-01 10:11:12")` for deterministic datetime
- Use `snapshot.assert_match(value=data, name="Result")` for complex structures

## Arrange-Act-Assert
- Every test has `# Arrange`, `# Act`, `# Assert` comment labels
- For exception tests, use `# Act & Assert` wrapping `pytest.raises()`
- Do not omit these labels — they make test intent immediately scannable

## Mocking — StorageMock Pattern
```python
class StorageMock:
    @pytest.fixture
    def storage(self):
        from app.storage_interfaces.storage_interface import StorageInterface
        return create_autospec(StorageInterface)
```
- One `@pytest.fixture` per storage interface, imports **inside** fixture body
- Use `create_autospec()` for ALL storage interface mocks
- Import interactor class **INSIDE** the `interactor` fixture (never at module level)
- Use `common_fixtures/adapters/` helpers for service adapter mocking — never inline `mocker.patch()`
- **Mock methods as methods, never as bare attributes** — stub a method with `.return_value` (`data_store.get_bps_template_id.return_value = "x"`) or `create_autospec()`, never as a bare value (`data_store.get_bps_template_id = "x"`). A bare-attribute stub turns the call site `obj.get_bps_template_id()` into "call a string", which either errors loudly or — worse — the bug under test is a parens-less `obj.get_bps_template_id` (property-vs-method confusion), and the bare stub makes that no-op pass GREEN. Real case: a method-vs-property mismatch silently made an import a no-op; the gap only showed once the mock used `.return_value`. The data-store API shape is genuinely inconsistent — `get_bps_template_id` is a `@property` in `bps/configio/pipeline/data_store.py` but a plain method in `bps/configio/bps_template/data_store.py` — so the mock must mirror the real call shape, not guess it.

## Assertions
- `assert_called_once_with(<exact_kwargs>)` on ALL storage/adapter calls
- `assert_not_called()` on methods that must NOT be reached in error paths
- Never leave a test with only `pytest.raises()` and no storage call assertions
- For success tests: assert every meaningful attribute of the return DTO

## Test Data — Factory Boy
```python
class EntityDTOFactory(factory.Factory):
    class Meta:
        model = EntityDTO
    entity_id = factory.Sequence(lambda n: f"entity_{n+1}")
    name = factory.Sequence(lambda n: f"name_{n+1}")
    status = EntityStatus.ACTIVE.value
```
- DTO factories inherit `factory.Factory` (NOT `DjangoModelFactory`)
- Use `factory.Sequence` for unique values, `factory.Iterator` for cycling
- `create_batch(size=3)` for multiple instances
- `reset_sequence(0)` in tests needing deterministic values
- Check `<app>/tests/factories/` for existing factories before creating new ones
- **Never pass `<factory>_id=<string>` to satisfy a FK — let the `SubFactory` build the parent.** Passing a raw id string bypasses the `SubFactory` and creates a dangling FK. On sqlite this does NOT fail in the test body — the FK is only checked at TEARDOWN, so the test passes GREEN and teardown ERRORs (a confusing, misattributed failure). Set the related object (`entity=EntityFactory()`), not its id, and let the `SubFactory` chain build the parent row.

## Shared Fixtures
- **Use `conftest.py`** for scaffolding shared across 2+ test files — never duplicate it across files. **"Scaffolding" is not just fixtures**: it covers plain helper/builder functions (`build_actor`), mock factories, stub constructors, and base classes. *(This clause was fixture-scoped until 2026-07-20 and kept missing the real cases — two of the three REF-001 sightings were plain module-level helpers, not fixtures, so the rule read as not applying. It applies.)*
- **Divergent copies are worse than duplicate ones.** Two same-named helpers with DIFFERENT defaults (`build_actor` with `role_identification_ids=["role_1"]` in `conftest.py` vs `[]` in `enrolment_mocks.py`) mean a reader who finds one copy assumes it is the one in play — and inside conftest the nearest definition genuinely shadows. Either hoist one copy and import it, or name the variant for how it differs (`build_actor_without_roles`). *(Hook-enforced: `check-duplicate-test-scaffolding.py` blocks a change that AUTHORS a divergent same-named helper in the same app's tests tree. It deliberately ignores pre-existing pairs — ~2% of this repo's 12,315 test files already carry one — so the hook never blocks an unrelated edit. Identical copies it does not catch: those are still yours to spot.)*
- **Shared fixture on the base class, only the varying one per-file.** When N test files each define a `StorageMock` subclass and share a fixture that depends ONLY on base fixtures + one per-file override, the shared fixture lives on the base `StorageMock` class (in `conftest.py`); only the genuinely-varying fixture stays per-file. The trap: adding a "shared" fixture directly onto each per-file subclass is syntactically identical to adding a real override, so copy-paste feels correct — it is a duplication bug. If an `interactor`/mock fixture is byte-identical across the files and only e.g. a `*_provider`/`*_fact` fixture differs, hoist the identical one. *(Caught at review twice — S1 and S2 guard batteries; 11 files carried an identical `interactor` fixture.)*
- Place `conftest.py` at the appropriate level: `tests/conftest.py` for app-wide, `tests/interactors/conftest.py` for sub-module
- **Full fixture doctrine** (factory-vs-fixture-vs-builder division, scoping, autouse bounds, sprawl control): `.claude/rules/references/fixture-doctrine.md` — load before authoring fixtures or scenario builders

## Contract Tests
- Contract tests must match actual implementation state
- If a method has a real implementation, do NOT test that it raises `NotImplementedError` — that produces false positives
- After writing contract tests, verify each test exercises the code path it claims to test

## Coverage Requirements
- **All public methods** need tests — both `validate()` AND `execute()` for plugins/nodes
- **Success + failure paths** — at minimum one success test and one error/exception test per method
- **Registry error cases** — test exception paths for registration failures, missing entries, duplicate keys
- **ConfigIO foreign-scope rejection** — every configio/populate entity that writes a scoped record MUST have a test where a row carries a foreign scope id (`account_id` / `pipeline_item_template_id` / `portal_id`) and asserts the REAL setter/storage method is `assert_not_called()`, proving the authorised-scope guard runs before any write. See the tenancy rule in `configio-architecture.md`. This bug class shipped past green suites three times — the test is the only proof the guard exists.
- **Test file size limits apply** — test files follow the same 500-line hard limit as production code. Split large test files by concern.

## Test Protection
- **Never remove, weaken, or skip existing tests** — if a test fails after your change, fix the code or update the test to match new behavior, don't delete the test

## Forbidden
- No `MagicMock()` for DTOs — use factories
- No private `_setup_*` helpers — use pytest fixtures
- No testing private methods — test via public interactor method
- No module-level interactor imports — import inside fixtures
- No duplicated fixtures across test files — use conftest.py
