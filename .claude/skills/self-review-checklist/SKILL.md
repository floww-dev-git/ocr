---
name: self-review-checklist
description: "Mandatory pre-commit checklist that verifies common issues from review history. Run this during Stage 3 (Self-Review) of the dev loop. Reads agent memory for latest patterns and checks changed files against known issue categories."
argument-hint: "[app_name or file paths to review]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash
---

# Self-Review Checklist

Run this checklist against all files changed in the current task. This is NOT optional — it gates Stage 4 (Independent Review).

## Step 0: Load Latest Issues

Read `.claude/agent-memory/developer/MEMORY.md` and `.claude/agent-memory/reviewer/MEMORY.md` to get the current list of recurring issues. Apply ALL patterns from memory during this review. For multi-task plan work, also load `.claude/rules/references/engineering-canon.md` — its Review lines are the invariant phrasing of these checks.

## Step 1: Identify Changed Files

Run `git diff --name-only HEAD` (or `git diff --name-only` for unstaged) to get the list of changed files. Review EVERY changed `.py` file.

## Step 2: Run Automated Checks

For each changed Python file, verify:

### A. DRY Violations (Issue #1 — most common)
- Search the codebase for code blocks similar to what you just wrote
- If you created a utility function, verify it replaced ALL existing duplicates
- Check: `grep -rn` for any 3+ line block that appears in multiple files in your changeset

### B. Cross-App Imports (Issue #2)
- Scan imports: no `from other_app.adapters.` or `from other_app.storages.` or `from other_app.interactors.`
- Only `from other_app.app_interfaces.` is allowed

### C. Error Handling in Delegating Methods (Issue #7)
- Every `execute()` method that calls a service adapter or external interface should have try/except
- Every thin wrapper must handle failure gracefully — not assume success
- Check: search for service adapter calls without surrounding try/except

### D. Null Guards (Issue #6 from reviewer)
- Every object returned from a service call or storage lookup must be None-checked before attribute access
- Check: look for `result.attribute` without a preceding `if result is None` or `if result:`

### E. Truthiness vs None (Issue #9)
- In validation logic, use `is not None` instead of `if value` when 0, "", or [] are valid
- Check: search for `if value` or `if not value` in validation/config code

### F. Dead Code (Issue #8)
- Every class, method, schema declared is actually used and wired in
- No config dataclasses without corresponding deserialization logic
- No base class methods designed but not implemented

### G. Test Quality (Issues #10, #11)
- Test files under 500 lines — split if exceeded
- Every public method has success + failure tests
- `execute()` paths tested, not just `validate()`
- Shared fixtures in `conftest.py`, not duplicated
- Contract tests match actual implementation (no false NotImplementedError tests)

### H. File Size
- Production files under 500 lines (200 target)
- Functions under 50 lines, max 3 args, max 3 indentation levels

### I. Domain Terminology Consistency
- Variable names, exception names, and DTO fields match the exact terms from user stories / acceptance criteria
- No developer-invented synonyms for domain concepts
- Business formulas match the user stories exactly (no assumed or guessed formulas)
- Service/API method names are NOT incorrectly renamed when domain concepts are renamed in docs

### I2. Comments & Names (hard check — the design record does not live in source)
Read every comment and docstring you added in this changeset (`git diff` the added lines, not the whole file):
- **Delete rationale prose** — any comment explaining WHY a shape was chosen, what invariant it upholds, or what it was chosen over. That belongs in the ADR.
- **Delete every `ADR-`/`US-`/`AC` citation in production source** — the design record is the ADR. Citations in TEST files are fine (AC traceability). *(`quality-gate.sh` Check 6 flags these on edit.)*
- **Delete restatement** — a comment or docstring that says what the code already says, and contract narration on DTOs / `@abc.abstractmethod` bodies.
- **Keep** only a one-line non-obvious mechanical fact the code cannot carry, and `app_interfaces/` public-contract docstrings.
- **Names**: no metaphor nouns (`footprint`, `snapshot`, `envelope`) and no class name that needs the ADR to decode. Test: could a reader who has never seen the design doc say what it holds or does?

See `clean-code.md` → "Comments — the design record does not live in source" and the metaphor-noun naming rule.

### J. Scope Drift (hard check)
- Check the diff stays within the active ADR's `**Declared modules:**` fence — every changed
  path must sit under a declared module (no ADR / ad-hoc bug work = passes with a note)
- On drift, do NOT silently widen the fence — route via the Design Correction Protocol
  (re-scope through the architect + manager; never patch the declaration yourself)

### K. ConfigIO Cross-App Isolation (only if touching bps/configio/ or <owning_app>/interactors/configio/)
- IO orchestration files are in `bps/configio/<module>/`, domain logic in `<owning_app>/interactors/configio/<entity>/`
- No direct owning-app imports in `bps/configio/<module>/run_actions_handlers/` or `action_generators/`
- All cross-app calls go through `get_service_adapter().<owning_app>_service.<method>()`
- Checkers receive typed DTOs — no `asdict()` calls, no dict key access on DTO objects
- `import_interactor.py` calls `ImportInteractor(import_store=...).execute()` — no custom loops
- `export_interactor.py` in bps is a thin wrapper only

### L. Test Existence & Cases Coverage Gate (BLOCKING — must pass before verdict)

For EVERY new or significantly modified interactor, storage method, or adapter method in this changeset:
- A corresponding test file exists (`app/tests/test_<module>.py` or `app/tests/unit/test_<module>.py`)
- Each new public method has at least one success-path test and one failure-path test
- **When a tasks file drives the work: every entry on the task's `Cases:` line has a corresponding test** — the list is the coverage contract, generic success+failure is not enough
- Tests were run: `pytest path/to/test_file.py -v --no-migrations` — all pass

**Verification step:** List all changed production files → list corresponding test files → confirm 1:1 coverage (and `Cases:`-entry coverage for in-plan work).

If ANY production file (interactor, storage, adapter) lacks a corresponding test file → **FAIL. Do not proceed to verdict.**
This check is BLOCKING — it cannot be overridden by other passing checks.

Exception: User explicitly said "skip tests" or "tests later" for this specific task.

## Step 3: Report

Output a structured report:

```
## Self-Review Checklist Results

| Check | Status | Notes |
|-------|--------|-------|
| DRY | PASS/FAIL | ... |
| Cross-App Imports | PASS/FAIL | ... |
| Error Handling | PASS/FAIL | ... |
| Null Guards | PASS/FAIL | ... |
| Truthiness | PASS/FAIL | ... |
| Dead Code | PASS/FAIL | ... |
| Test Quality | PASS/FAIL | ... |
| File Size | PASS/FAIL | ... |
| Domain Terminology | PASS/FAIL | ... |
| Comments & Names | PASS/FAIL | ... |
| Scope Drift | PASS/FAIL | ... |
| ConfigIO Isolation | PASS/FAIL/N-A | ... |
| Test Existence & Cases | PASS/FAIL | ... |

**Verdict: PASS / FAIL (N issues to fix)**
```

If ANY check is FAIL, fix the issues and re-run this checklist. Do NOT proceed to Stage 4 with failures.
