---
name: dev-loop
description: Execute one iteration of the dev loop (RED->GREEN->REFACTOR per Cases: entry -> VERIFY -> SELF-REVIEW -> [INDEPENDENT REVIEW: slice's first task only] -> INTEGRATE -> LOCAL COMMIT[auto]) for a single task. Test-first; commits are per-task and automatic; independent review is per-slice; the user's single gate per plan is the end-of-plan PUSH. Use when implementing a task from the task list.
argument-hint: "[task description or task number from task list]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Dev Loop — Single Task

Execute the dev loop for: $ARGUMENTS

Follow `@.claude/rules/dev-loop.md` strictly. No stage can be skipped.

## Stage 1: Red — Failing Test First

1. **Understand the task** — read the task line: its `Cases:` list (happy · failure · edge, each AC-traced — authored at planning time) and its ✔ criterion; identify exactly what behaviour to prove
2. **Load context** — read relevant files, existing patterns, CLAUDE.md files
3. **Search for reuse** — find existing interactors, storages, DTOs that can be reused
4. **Write the failing test for ONE `Cases:` entry** — red-green-refactor is a loop: one case's failing test, the minimum code to pass it (Stage 2), refactor on green, then back HERE for the next entry until the list is exhausted. Never re-derive cases from the code; the list is the approved case set and the ✔ criterion is the exit assertion. A task missing its `Cases:` line is an authoring error — flag it (Design Correction Protocol), don't improvise
   - Use `/interactor-test-writer` or `/write-integration-testcase` as applicable
   - Error/validation cases first, success cases last
   - A genuine case the list missed is a Design-Correction flag on the tasks file, never a silent addition
   - Consumer-first: wire real the collaborators already built earlier in the slice (entities, DTOs, domain objects); autospec the storage interface the interactor drives out and any cross-module ports (their impls land later) — the StorageMock pattern
5. **Run it and watch it fail for the RIGHT reason:**
   ```bash
   pytest path/to/test_file.py -v --no-migrations
   ```
   An import error or typo failure is not red — the test must fail on the missing behaviour.

## Stage 2: Green — Minimal Implementation, then Refactor (loops with Stage 1)

1. **Invoke the matching workflow skill** — check the Workflow Routing table in the project `CLAUDE.md`. If a skill matches the current task, invoke it via the Skill tool before writing code. This is not optional.
2. **Write the minimum code that passes THIS case** — no code for cases whose tests aren't written yet
3. **Run tests — all must pass.** If any fail → fix and re-run. Do NOT proceed with failures.
4. **Refactor on green** — naming, extraction, clean-code limits; re-run tests, they stay green.
5. **Loop:** more entries on the `Cases:` list → back to Stage 1 for the next one. List exhausted and all green → proceed to Stage 3.

## Stage 3: Self-Review

Run `/self-review-checklist` against the changed files. This skill checks all known recurring issues from review history (DRY, cross-app imports, error handling, null guards, truthiness, dead code, test quality, file size).

Additionally check:
- **Clean code:** functions <50 lines, max 3 args, descriptive names, no magic numbers
- **Architecture:** DTO boundaries, interface deps, no layer skipping
- **Exception handling:** specific exceptions only, no bare except

The checklist must report PASS before proceeding to Stage 4. Fix all FAIL items first.

## Stage 4: Independent Review — CONDITIONAL (slice's first task only)

Review is **per slice**, not per task (`dev-loop.md` Review Per Slice, Not Per Task). This stage fires here only for the slice's FIRST task — the design-setting one (the interactor + the contracts it drives out), where a wrong shape cascades into every later task.

- **Later task in the slice?** Skip this stage — say so in one line ("Task 2.4, not slice-first — review rides the slice pass") and go to Stage 5. Your self-review (Stage 3) + the hooks are the per-task gate.
- **Slice's first task, or you're self-flagging a Critical, or the task lands a novel engine surface?** Run it:

1. **Invoke `reviewer` agent** (`model: sonnet` — code review; `opus` only for an architecture/NFR/parity pass)
2. Reviewer produces structured findings (Critical / High / Medium / Low)
3. **Address all Critical and High findings** before proceeding
   - Each fix goes through its own mini self-review
   - If fixes change behavior → re-run tests (back to Stage 2)
4. Medium/Low findings: fix now or note for follow-up

**The slice's own review** happens after its integration closer passes — the orchestrator (manager or `task-coordinator`) spawns the reviewer over the whole slice → `s<N>-slice-review.md`. Not your call to make from inside a task.

## Stage 5: Integrate

1. **Run the full app test suite:**
   ```bash
   pytest app_name/tests/ -v --no-migrations
   ```
2. **Verify:** no regressions, no broken imports, migrations run if applicable
3. If anything breaks → fix within this loop

## Stage 6: Local Commit (automatic, per task — the user gate is the PUSH)

Per `.claude/rules/dev-loop.md` "Commit Frequently, Gate Once": commit THIS task's changes now, locally, announced not asked ("Committed: `feat: ...` — 4 files"). Never push here — the push gate fires once at end-of-plan with the full commit series.

  1. **Stage specific files** — never `git add .`, always name files explicitly
  2. **Exclude**: `.env`, credentials, debug prints, commented-out code, unrelated changes
  3. **Conventional commit** — `feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`
  4. Subject line describes "why", under 70 chars — one atomic commit per task (compiles + tests green independently)
  5. Never amend or squash already-made task commits, never force-push — the atomic series IS the value (bisectability, per-task revert)

**Two mechanics that cost every agent on a feature a wasted cycle until they learn them:**

- **`black` reformats and ABORTS the first commit attempt, every time.** Expect it; it is not a failure. The sequence is: stage → commit (hook rewrites your files, commit aborts) → **re-stage the rewritten files** → re-run the task's tests (formatting can move a line a test asserts on) → commit again. Budget the second attempt instead of debugging the first. Never reach for `--no-verify`.
- **The git index is a SHARED file — commit with `git commit --only <paths>`.** When two lanes share one checkout (parallel workers, a coordinator plus a dev), a plain `git commit` commits the whole index, sweeping the other lane's staged work into your commit. `--only` restricts the commit to the paths you name regardless of what else is staged. This is `Shared-File Discipline` applied to the index: one writer per file, and you cannot re-read the index the way you re-read a tasks file. *(A near-miss on relieve-v2 was caught only because the formatting hook aborted the commit first.)*

## Completion

- Tick the task in the tasks file (tick-evidence hook verifies the ✔ artifact); in orchestrated plans the **manager** logs completion in `feature-context.md` — update it yourself only when working solo
- Show test summary to the user
- **In a multi-task plan, report-back only** — "Task complete. [X] tests passed. Committed `<hash>`. Proceeding to next task." No approval prompts.
- **At end-of-plan or for single-task work**, present the commit series (hash · subject · files per task) + test report for the PUSH gate.
- **Scout nudge (path-triggered, end-of-plan only):** if any changed file in the plan matches `sales_crm_graphql/`, `ext_client_graphql/`, `floww_cli_graphql/`, `portals/`, or any app's `mutations/`/`queries/` dirs (the same list as the schema-regen check), append ONE line to the end-of-plan presentation: "User-facing GraphQL/portal surface shipped (`<paths>`) — consider `@scout` for a gamma E2E validation after merge/deploy. Recommendation, not a gate; does NOT substitute for reviewer/security — scout runs after them, against the deployed environment." Backend-only plans get zero mention.
