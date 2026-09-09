# Dev Loop

## Feature Lifecycle vs Dev Loop

The **Feature Lifecycle** is the outer pipeline managed by the `manager` agent:
```
PRD → User Stories [APPROVE] → ADR [APPROVE] → Implementation Plan [APPROVE]
  → Dev Loop (per task, no commit gate between tasks) → Review per SLICE (+ the slice's first task)
  → End-of-plan Commit+Push [APPROVE — single gate, all batched tasks]   (security auto-review disabled — see ✱)
  → Promote to Envs [ONE prompt — select target env branches]
```
✱ **Security auto-review is TEMPORARILY DISABLED (2026-07-10, user request).** The `@security` agent still exists for MANUAL invocation on sensitive changes (`iam/`, `payments_engine/`, `ib_payments/`, `bps/`, `tdr/`) — it is no longer auto-triggered in the pipeline. Re-enable by restoring the Security step in the lifecycle above and the sensitive-path → security rows in `references/agent-teams-pipeline.md`.

\*\* **Promote to Envs** runs automatically after push confirmation. Manager asks the user ONE question — which of the five canonical env branches (`alpha`, `beta`, `gamma`, `tg-bn-gamma`, `tg-bn-uat`) need a PR. Developer then executes the mechanical sequence (per-env integration branch, merge, push, `aws codecommit create-pull-request`). Drive via `/promote-to-envs`. `tg-bn-prod` is intentionally excluded — prod promotion is a separate release-management step.

The **Dev Loop** below is the inner loop executed per task within the Implementation phase.
The `manager` drives the outer pipeline automatically between approval gates.
The `developer` executes the inner dev loop per task.
These two loops are nested — do not conflate them.

**The 4 approval gates** (the only user pauses):
1. After requirements (PRD + user stories, one deliverable)
2. After ADR
3. After implementation plan
4. Before push (per-task local commits are automatic; one gate approves the series + pushes)

Review is per-SLICE (plus the slice's first task), and is NOT a user gate when clean — only Critical/High findings pause. (Security auto-review is temporarily disabled — see ✱ above.)

**Inner-loop delegation (optional).** For a slice with real inner-loop volume, the manager delegates the *between-gate* driving of that slice to an ephemeral `task-coordinator` (depth-1) instead of spawning workers itself. The coordinator runs the per-task dev/review/fix/tick/commit loop, absorbs the task firehose, and returns a compact summary — the manager keeps every user gate at depth-0 and the push gate at end-of-plan. See `.claude/agents/task-coordinator.md` and `references/agent-teams-pipeline.md` (Who Drives the Auto-Chain).

Every task goes through these stages in order. Two stages are cadence-bound rather than per-task: **Independent Review** fires on the slice's first task and once per slice (see "Review Per Slice, Not Per Task"), and the **Push** rides one end-of-plan gate while each task commits locally and automatically (see "Commit Frequently, Gate Once").

```
Per task: ANALYZE → ┌─ per Cases: entry ─┐ → VERIFY → SELF-REVIEW → INTEGRATE → LOCAL COMMIT (auto) → next task
            ↑       │ RED → GREEN → REFACTOR │                     │
            │       └──────── ⟳ ─────────────┘                     │
            └──────────────── fix if any stage ────────────────────┘

  ↳ slice's FIRST task only: + INDEPENDENT REVIEW before its commit (design-setting — cascade risk)

Per slice: all tasks done → INTEGRATION CLOSER (tester) → INDEPENDENT REVIEW (whole slice) → fix Crit/High → next slice

End of plan: ◆4 PUSH GATE — present the commit series (one line per task), user approves ONCE, push
```

Red-green-refactor is a LOOP, not a line: it cycles once per entry on the task's `Cases:` list —
one failing test, the minimum code to pass it, refactor on green, then the NEXT case. A task
exits the cycle only when every case is green.

## Stages

Test-first (red-green-refactor). WHY: writing the test first makes the task's ✔ criterion
executable before the code exists — a false "done" becomes structurally impossible (pairs with
the tick-evidence hook), and outside-in the failing test derives the collaborator contracts
(engineering-canon: GOOS, red-green-refactor).

1. **Red** — take the NEXT entry from the task's `Cases:` list (every task carries one, authored at planning time — happy path · failure paths · edges, each traced to an AC or Error-Scenarios row; depth follows decision density; see the Tasks-File Contract in `/task-breakdown`) and write its failing test — error/edge cases before the happy path. Consumer-first: the interactor is built before its storage — autospec the storage interface it drives out (the StorageMock pattern, testing.md) and any cross-module ports; wire REAL only the collaborators already built earlier in the slice (entities, DTOs, sibling domain objects). Build-once — this same mock-tested interactor is what the integration closer later wires to the real storage. Run it; watch it fail for the RIGHT reason. The slice's final sub-task is its integration suite (stories + ACs end-to-end via `/write-integration-testcase`) — unit tests ride each task, integration rides the slice closer
2. **Green** — implement the minimum that makes THIS case pass — no code for cases not yet written
3. **Refactor** — on green only: naming, extraction, clean-code limits; tests stay green. **Then loop to Red for the next `Cases:` entry** — the cycle ends when the list is exhausted and all green
4. **Verify (conditional)** — fires only if this task's deliverable produces an artifact unit tests cannot assert directly (generated PDF/letter, `schema_gen` schema file, CSV/export output, HTML report). If so: locate the specific existing generator/notebook for that domain (do NOT blind-glob `*.ipynb` at repo root — the 450+ root notebooks are one-off ops/migration scripts, several destructive), run it, inspect the output, present it before Self-Review. No such artifact → skip and say so in one line ("No artifact output — unit tests are the verification")
5. **Self-Review** — run `/self-review-checklist`
6. **Independent Review** — `reviewer` agent reviews; fix all Critical/High findings. **Fires on the slice's FIRST task, then once per SLICE** (after the integration closer), not on every task — see "Review Per Slice, Not Per Task" below
7. **Integrate** — run full app test suite, fix any regressions
8. **Local Commit (automatic, per task)** — after INTEGRATE passes, commit THIS task's changes locally: conventional format, atomic (compiles + tests green), specific files staged, announced not asked. See "Commit Frequently, Gate Once" below. The user gate is the PUSH, once per plan.
   - **GraphQL Schema Regeneration**: if staged files touch `sales_crm_graphql/`, `ext_client_graphql/`, `**/mutations/`, or `**/queries/`, regenerate schemas before committing:
     ```bash
     python manage.py schema_gen --schema sales_crm_graphql.schema.schema
     ```
     If `ext_client_graphql/` was also modified:
     ```bash
     python manage.py schema_gen --schema ext_client_graphql.schema.schema --out ext_client_schema --schema_enum EXT_CLIENT_SCHEMA
     ```
     Stage the regenerated schema files before committing.

## Commit Frequently, Gate Once (amended 2026-07-04 — user ruling)

### WHY
The original batching rule solved N approval round-trips but conflated approval frequency with COMMIT frequency — a 10-task plan carried hours of work uncommitted (unrecoverable on a crash, un-bisectable, one wall-diff at the gate). The fix separates them: commits are frequent and automatic; the user's ONE gate per plan approves the series and the push.

### Rules
- **Per-task local commit (automatic)** — after each task passes INTEGRATE, the developer commits that task's changes locally: conventional format, atomic (compiles + tests green independently), specific files staged, ANNOUNCED not asked ("Committed: `feat: ...` — 4 files"). No user interaction, no pause.
- **NO user gate between tasks** — the developer reports completion, the manager logs it, the pipeline auto-advances. Unchanged.
- **End-of-plan PUSH gate (◆4)** — after the final task, the manager presents the COMMIT SERIES (one line per commit: hash · subject · files) + the test report. One approval covers the series and the push. This is the plan's single user gate.
- **Single-task work** (ad-hoc fix, Sentry) — the same, degenerate case: one commit, then the push gate.
- **Mid-plan push override** — user says "push now" → push the committed-so-far series, resume the plan.
- **Safety valve** — at 10+ tasks committed-but-unpushed, the manager SUGGESTS an interim push (work is already crash-safe locally; the valve now guards against divergence, not loss).
- **Plan failure mid-stream** — completed tasks are already committed; nothing sits at risk while the bad task is debugged. Present the push gate for the good series if the plan pauses long.
- **Never rewrite the series** — no squash/amend of per-task commits at the gate; the atomic history IS the value (bisectability, per-task revert).

### What this changes
- Developer: commits locally at every task close-out (announce), pushes NEVER (the push rides the gate).
- Manager: presents the series + push gate at end-of-plan; no commit prompts anywhere.
- Reviewer: unchanged — review still precedes the task's commit (nothing unreviewed gets committed).
- Promote-to-envs: unchanged — runs after the push as today.

## Review Per Slice, Not Per Task (amended 2026-07-16 — user ruling)

### WHY
Per-task review is **blind to cross-file patterns** — it sees one task's files, so a shape repeated across a slice survives every pass. Real case: 11 files carried an identical `interactor` fixture, caught only at S1 *and again* at S2 (`testing.md`), after a dozen clean per-task reviews. A slice-wide reviewer sees all 11 at once. The cost was also real (REF-001: 37 reviews, 7,634 lines, 81% clean on the first pass — most per-task gates were toll booths), but **the cross-file blindness is the reason**, not the token bill: reviewing the slice makes the review *better*, not just cheaper.

### Rules
- **The slice's FIRST task is reviewed immediately.** Consumer-first puts the interactor + the contracts it drives out at task 1; everything later implements against it. That is where a wrong shape cascades, so it does not wait. (REF-001: `s3-task-2.1`, the `ExecuteTransitionInteractor`, is one of the seven that came back CHANGES REQUESTED.)
- **The slice is reviewed once, whole, after its integration closer passes** — the reviewer judges proven behaviour, and reads for the shape findings only slice altitude reveals: duplication, fixture copy-paste, naming drift, an extension point that never materialized.
- **Later tasks are not individually reviewed.** Their findings are leaf-level and don't cascade; the slice pass catches them.
- **Model tier follows the review kind, not the path:** architecture · NFR · parity · engine-boundary → `opus`; per-slice code review and the first-task review → `sonnet` (default). Checking code against known standards is pattern-matching; judging a design is not.
- **Escape hatch** — a task that lands a novel engine surface, or a Critical the developer self-flags, gets its review immediately. Don't hoard a known problem until the slice closes.
- **Unchanged:** Critical/High pause the loop and route via `/impl-review-points`; clean auto-advances with no user gate; the tester still owns the closer; `security` stays manually invoked (✱).

### The invariant this moves — deliberately
`Review before commit` becomes **`review before PUSH`**. Later tasks now commit before their slice review. That is safe and intended: per-task commits are **local and unpushed** checkpoints, and the push gate (◆4) sits at end-of-plan *behind* the slice review — so nothing unreviewed has ever reached the remote, which is what the original rule was protecting. The atomic per-task history stays (bisectability, per-task revert); a slice-review finding is fixed in a follow-up commit on the same series, never by rewriting it.

Use `/dev-loop` skill for detailed procedural guidance on each stage.
Requirement analysis gate and fast-path rules are in `agent-delegation.md` (Pre-Implementation Gate).
Context resumption rules are in `worktree-workflow.md`.

## Exit Criteria

All must be true before starting the next task:
- Requirement analysis completed and approach approved by user (or explicit skip)
- For artifact-producing tasks only: the artifact was generated, inspected, and presented (Verify stage); all other tasks state the one-line skip
- Unit tests written and passing
- No clean code or architecture violations
- Self-review passed; for the slice's FIRST task only, independent review passed (no open Critical/High findings)
- Full app test suite passes (no regressions)

Per-task exit criteria INCLUDE the automatic local commit (see "Commit Frequently, Gate Once") — a task isn't closed until its green state is checkpointed.

End-of-plan exit criteria (in addition to per-task criteria for every task):
- **Every slice carries a clean slice review** — saved to `<app>/docs/features/<slug>/reviews/s<N>-slice-review.md` with no open Critical/High. No slice reaches the push gate unreviewed
- The commit series presented at the push gate (one atomic conventional commit per task) and pushed on approval
- Feature context Active pointer + phase advanced (tasks-file ticks are the completion record — no mirrored list)
- AI readiness gate passed — new apps have `CLAUDE.md`, new significant modules have context, project `CLAUDE.md` updated (see `ai-readiness-gate.md`)
- Unit tests written for ALL new/modified interactors, storages, and adapters — test files must exist, not just pass

## Design Correction (plan wrong mid-implementation)

When implementation reveals a planning artifact (PRD, stories, ADR, tasks) is wrong: HALT the
affected task, do NOT work around it. Load `references/dev-loop-corrections.md` and follow the
Design Correction Protocol. The main session coordinates; each agent owns its own documents.

## Rules

- **Analyze before implementing** — don't write code for a new feature without completing requirement analysis first. This gate prevents the most expensive rework
- **Verify artifacts before declaring done** — if the task's deliverable is a generated artifact (PDF, schema file, export, report), produce and inspect it via that domain's specific generator; never present artifact-producing changes as complete on unit tests alone. Never blind-execute repo-root notebooks — they are ops/migration scripts, several destructive
- **No batching** — never implement multiple tasks then test them all at once. Batched changes make failures harder to isolate and bisect
- **No debt forwarding** — if something breaks, fix it now, not in a later task. Deferred fixes compound and block downstream tasks
- **Test what you build** — the developer authors RED for every task in an active dev-loop cycle: the test derives from and drives the implementation, so it cannot be delegated mid-task. The `tester` owns (a) each slice's integration-suite closer sub-task (story/AC-driven — the independent verification seat), (b) backfilling tests on already-shipped code, (c) standalone test-writing line items, plus the feature's test-suite report and coverage report at end-of-plan. Either way, tests must exist and pass before self-review
- **Self-review before independent review** — `reviewer` agent sees code only after self-review passes
- **Review before push** — no code is PUSHED without passing independent review (per-slice; plus the slice's first task). Later tasks may commit locally before their slice review — those commits are unpushed checkpoints, and the push gate sits behind the slice review. See "Review Per Slice, Not Per Task"
- **Docs live with the owning app, one folder per feature** — ALL of a feature's artifacts live together under `<owning_app>/docs/features/<feature-slug>/`, organized and named per `.claude/rules/references/feature-folder.md` (the single home of the layout) — never scattered by type across app docs, never centralized. The app that owns the business logic owns the docs; multi-app features keep one home in the primary owning app. **User stories are the one artifact outside the feature folder** — they are epic-scoped, not feature-scoped (an epic outlives a feature), so they live at `<owning_app>/docs/user_stories/<epic-slug>.md` — still with the owning app. Standalone one-off ADRs (no feature) go to `<app>/docs/adrs/`
- **Push gate** — local per-task commits are automatic (announced, never asked); the user's single approval per plan is the PUSH gate at end-of-plan, where the commit series + test report are presented. Nothing is ever pushed without that approval; nothing green ever sits uncommitted. See "Commit Frequently, Gate Once".
- **Fresh session at task boundaries on long plans** — for long multi-task plans (especially configio), prefer handing off to a fresh developer session at a task boundary over resuming a context-saturated transcript. Resumed saturated sessions have hit the context limit mid-plan; a fresh session re-orients cleanly from `feature-context.md` + `git status`. Keep per-task context lean: scoped reads, summarized test output. See developer agent memory.

## Agent Teams

For team spawn conditions, templates, and review team composition, see `references/agent-teams-pipeline.md`.
Dev team triggers at 4+ independent tasks; review team triggers at 6+ changed files.
