---
name: interactor-test-writer
description: Step-by-step interactor test case writer for Django CRM using Clean Architecture patterns. Validates test location, lists test cases for approval, mocks storage interfaces and adapters, generates DTO factories, and implements tests with Arrange-Act-Assert structure using pytest and Factory Boy. Use when user says "write interactor tests", "test this interactor", "create test cases for interactor", "write unit tests", or mentions interactor testing.
argument-hint: "[interactor path or name]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Interactor Test Writer

Follow @.claude/rules/testing.md for all testing standards (mocking, assertions, factories, forbidden patterns). Before creating any fixture or shared setup, load `@.claude/rules/references/fixture-doctrine.md` (division of labor, scoping, autouse bounds, duplicate-scan).

## Workflow

Follow these steps in exact order. Do not skip steps or combine them.

### Step 1: Validate Test Location

1. Read the interactor file the user wants to test
2. Identify the Django app it belongs to (e.g., `ib_collections`, `sales_crm_core`, `bps`)
3. Determine the correct test directory:
   - Pattern: `<app>/tests/interactors/<sub_module>/test_<interactor_name>.py`
   - Check if a `storage_mock.py` file exists at `<app>/tests/interactors/storage_mock.py`
   - Check if a `common_fixtures/` directory exists at `<app>/tests/common_fixtures/`
4. Verify the test file does not already exist
5. Announce the location (announce-and-execute per `consent-granularity.md`) — ask only if two plausible locations genuinely conflict

### Step 2: Establish the Case List

**In-plan (a tasks file drives this work):** the task's `Cases:` line is the case set — AC-traced, authored at planning time, approved at Gate 3. Consume it directly; do NOT re-derive from code and do NOT gate on user approval (no per-sub-task gate per `/process-tasks-list`). Then VERIFY coverage: walk the interactor's execution paths (validations/exceptions, storage calls, interactor-to-interactor calls, adapter calls, happy path with side effects) — a path the list genuinely misses is a Design-Correction flag on the tasks file, never a silent addition.

**Ad-hoc (no tasks file):**
1. Analyze every execution path in the interactor:
   - All validation checks and their exception raises
   - All storage interface calls and their possible failures
   - All interactor-to-interactor calls
   - All adapter/service calls
   - The successful (happy) path with all side effects
2. List test cases: **validation/error cases first, success cases last**
3. Each test case: `test_<scenario_description>` with brief description
4. Present the list to the user and **wait for approval** before proceeding

### Step 3: Mock Storage Dependencies

1. Check if `StorageMock` exists in `<app>/tests/interactors/storage_mock.py`
2. Verify all storage interfaces used by the interactor are present as fixtures
3. Add missing fixtures to the existing `StorageMock` class
4. If `StorageMock` does not exist, create it with all required storage fixtures

For detailed mocking patterns, consult `references/mocking-patterns.md`.

### Step 4: Mock Other Interactors

1. Identify any interactor-to-interactor calls
2. Check `<app>/tests/common_fixtures/interactors.py` for existing mock helpers
3. If not found, create using the `get_mock` pattern in `common_fixtures/interactors.py`

For the `get_mock` helper pattern, consult `references/mocking-patterns.md`.

### Step 5: Mock Cross-App Adapters

1. Identify adapter/service calls (e.g., `ServiceAdapter`, `IamMixin`)
2. Check `<app>/tests/common_fixtures/adapters/` for existing adapter mocks
3. If not found, create adapter mock helper under `common_fixtures/adapters/`

### Step 6: Ensure DTO Factories Exist

1. List all DTOs used in the interactor
2. Check `<app>/tests/factories/` for existing factories
3. Create missing factories in `<app>/tests/factories/interactors/<relevant_module>_dtos.py`
4. Check for existing factories before creating — avoid duplication
5. After creating factories, add sequence resets to `conftest.py` if it has an auto-reset fixture

For detailed factory patterns, consult `references/factory-patterns.md`.

### Step 7: Implement Test Cases

Implement ONE test case at a time, in the approved order.

For test class structure and examples, consult `references/test-structure-patterns.md`.

**After implementing each test:**
1. Run the test: `pytest <test_file_path>::Test<Class>::test_<method> -v`
2. If it fails, analyze the error and fix
3. Move to the next test case

## Quality Checklist

Before finishing, verify:
- [ ] All approved test cases are implemented
- [ ] Each test has `# Arrange`, `# Act`, `# Assert` section comments
- [ ] Error cases tested before success cases
- [ ] All mock calls verified with `assert_called_once_with()` using exact kwargs
- [ ] Factory Boy used for ALL test data
- [ ] No duplicate DTO factories created
- [ ] Interactor class imported INSIDE the `interactor` fixture
- [ ] Storage interfaces imported INSIDE their fixtures
- [ ] Test methods under 50 lines, max 3 indentation levels
- [ ] All tests pass: `pytest <test_file_path> -v`
