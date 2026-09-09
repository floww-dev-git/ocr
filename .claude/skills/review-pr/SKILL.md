---
name: review-pr
description: Independent code review with structured findings by severity. Reviews architecture compliance, clean code, security, testing, and performance. Use before merging or after milestones.
argument-hint: "[feature name, file paths, or branch to review]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash
---

# Independent Code Review

Review: $ARGUMENTS

## Process

1. **Identify scope** — determine which files to review:
   - If a feature name: find all changed files on the feature branch vs target branch
     ```bash
     git diff --name-only alpha...feature/$ARGUMENTS
     ```
   - If specific files: review those files
   - If "latest changes": review uncommitted + last commit
   - **Scope-drift hard check:** the diff must stay within the active ADR's `**Declared
     modules:**` fence — every changed path under a declared module (no ADR = ad-hoc work,
     passes with a note). Drift is a High finding: either the plan missed a module or scope
     is smuggling — report it, never patch the declaration yourself

2. **Read all files in scope** — read every changed file completely. A diff lies by omission; the full file is the review's evidence base, and reading the callers is part of the job. Load `.claude/rules/references/engineering-canon.md` — its Review lines are the invariants behind the checks below.

   **Re-reviews are the exception — do NOT re-read from scratch.** A re-review reads (a) its own prior review section and (b) the hunks changed since that pass (`git diff <sha-at-prior-review>...HEAD`). Everything else you already read and already judged; re-reading it re-pays the full intake to re-confirm findings you resolved last pass. Pull a full file back in only when a hunk's context genuinely demands it — and say so in one line.

3. **Relevance gate — FIRST, in one line each.** The 13 checks below are the full battery; most changesets can only trip a handful. Before reviewing, scan the changed paths and declare which checks are **N/A** and why — one line, no hunting:

   ```markdown
   ## Applicability
   Applies: architecture · clean code · testing · consistency
   N/A: migrations (no models touched) · API contract (no graphql/) · concurrency (no shared
        mutable state) · dead contracts (no storage_interfaces/) · performance (no queries)
   ```

   A check is N/A only when the changeset **cannot** trip it — a path-level fact, not a hunch ("no `models/` in the diff", "no `graphql/` in the diff"). When in doubt, it applies. Declaring N/A is not skipping: the line IS the evidence the check ran. Reviewing "migration safety" on a test-only diff is not thoroughness, it's a search for something that isn't there.

   **Review against project standards:**

   **Architecture** (`@.claude/rules/clean-architecture.md`):
   - DTO boundaries respected
   - Interface dependencies only
   - App isolation (no direct imports from other apps' internals)
   - No layer skipping

   **Clean Code** (`@.claude/rules/clean-code.md`):
   - Functions <50 lines, max 3 args, max 3 indentation levels
   - Descriptive naming, no magic numbers, no dead code
   - DRY, type hints present

   **Exception Handling** (`@.claude/rules/exception-handling.md`):
   - No bare except or generic Exception catches
   - Domain-specific exceptions

   **Security:**
   - Permission checks present
   - No injection risks
   - No data exposure

   **Testing** (`@.claude/rules/testing.md`):
   - Tests exist for new code — missing tests for a new interactor/storage/adapter is a **Critical** finding
   - Error cases tested first
   - Proper mocking patterns
   - **`Cases:` coverage** — when a tasks file drives the work, every entry on each reviewed task's `Cases:` line has a corresponding test; an uncovered entry is a High finding

   **Performance:**
   - No storage calls in loops
   - Appropriate select_related/prefetch_related

   **Migration safety:**
   - New columns have defaults or are nullable; no table-locking ALTER on large tables; data migrations batched; reversibility verified

   **API contract:**
   - No breaking GraphQL schema changes (removed fields, changed types, removed Union members); deprecated fields carry `deprecation_reason`

   **Concurrency:**
   - Shared mutable state protected (`select_for_update`, `@transaction.atomic`); event handlers idempotent; no race conditions on status transitions

   **Backward compatibility:**
   - DTO changes don't break consumers; storage interface changes coordinated; event schema changes additive-only

   **Dependency direction** (`@.claude/rules/clean-architecture.md` Inter-App Communication):
   - Engine/mechanism apps: arrows point apps → engine (engine defines `ports/`, imports zero apps); flag `gateways/`-style consumer-adapters inside a stable abstraction
   - **Engine domain purity:** the engine core carries zero producer-domain vocabulary — a domain-named class or enum value in the engine (`ShortfallLimitGuard`, `transition_type = SHORTFALL`) is a leak even when imports are clean. Domain criteria/strategies/effects belong in the producer app. N fact ports the engine defines to pull N producer facts is the halfway-house smell — flag it (`clean-architecture.md` mode 2; canonical REF-001 `plugin-architecture.md`)

   **Dead storage contracts:**
   - Every storage-interface method has a consuming interactor call site — **this is yours to check by reading; no hook backs it** *(`check-dead-contracts.py` deleted 2026-07-29, 50% false-positive rate)*. Dynamic and out-of-glob call sites are real, so confirm a method is unused before flagging it

   **Consistency:**
   - Matches existing codebase patterns and naming conventions; deviations are findings unless an ADR decision card sanctions them

4. **Produce structured report — inside the length budget:**

   **The findings are the product; the prose is not.** A review is read by a developer who needs to know what to change, and by `/feature-retro`, which greps it. Neither reads your reasoning. Do the deep thinking — then ship the conclusions.

   | Section | Budget |
   |---|---|
   | Summary | 2 sentences |
   | Each finding | file:line + the issue + the fix — **≤3 lines** |
   | What Looks Good | ≤3 bullets |
   | Escaped Cases · Plan Defects · Learnings | 1 line each (`None` / `none` if empty) |
   | **Whole report** | **≤120 lines** (a re-review section: ≤60) |

   Over budget means the review is narrating its own process. Cut the narration, not the findings — if you genuinely have enough findings to blow the budget, that is a signal worth stating in one line, and the findings stay. **Never** cut a finding to fit.

   *(REF-001 baseline: 37 reviews · 7,634 lines · avg 206 · max 649. The 649-line review carried 6 findings — 108 lines of prose per finding.)*

   ```markdown
   # Code Review — [scope]

   ## Summary
   [1-2 sentence assessment]

   ## Applicability
   Applies: [checks] | N/A: [check (path-level reason)]

   ## Findings

   ### Critical (must fix before merge)
   - **[file:line]** — [issue]
     - Suggested fix: [concrete suggestion]

   ### High (should fix before merge)
   - **[file:line]** — [issue]
     - Suggested fix: [concrete suggestion]

   ### Medium (fix soon)
   - **[file:line]** — [issue]

   ### Low (minor)
   - **[file:line]** — [issue]

   ## What Looks Good
   - [positive observations]

   ## Escaped Cases
   None

   ## Plan Defects
   None
   ```

   **Escaped Cases** (required when a tasks file drove the review; omit for ad-hoc reviews): one line per Critical/High finding that is a behaviour/input/error-path the task's `Cases:` line should have listed and didn't — `ESCAPED-CASE: <tasks-file>#<task-id> [<Severity>] — <missed case>`. Code-hygiene findings never qualify. If none, write `None` explicitly. Full contract in `reviewer.md`.

   **Plan Defects** (required, hook-enforced): answer one question from the code you just read — **does it prove the plan wrong?** Not "did the developer follow the plan", but "is the plan itself wrong, stale, or unbuildable as written". One line per defect: `PLAN-DEFECT: <artifact + named decision/criterion> — <what the code shows> — <owner: manager|architect>`. Write `None` explicitly if the plan held.

   Look for: an ADR decision the code proves impractical · a task whose stated approach the implementation had to work around · an AC that is ambiguous, untestable, or contradicted by another · a story assuming behaviour the code shows does not exist · a design the code has quietly outgrown.

   *WHY this is a required section and not a nicety:* on this project the **planning artifacts have been wrong far more often than the code** — REF-001 logged 12 HALTs, essentially all indicting the plan, and three further plan defects surfaced in a slice already built, reviewed and committed. Until now those were found only when a developer happened to trip over one mid-implementation. You are the last reader who sees the plan and the finished code together; if you do not ask this, nobody does.

   A plan defect is **not** a developer finding. Do not route it via `/impl-review-points` — it goes to the Design Correction Protocol (`references/dev-loop-corrections.md`): the manager owns PRD/stories/ACs, the architect owns ADR/tasks. Report it and let the orchestrator route it. A plan defect does not by itself make the verdict CHANGES REQUESTED — judge the code on the code.

5. **Save review** to `<owning_app>/docs/features/<slug>/reviews/` — required, not optional: reviews are feature artifacts, tracked with the branch; `/feature-retro` greps the `reviews/` folder.

   **Filename — the slice prefix comes FIRST and is mandatory** (convention only — no hook checks this since 2026-07-29):

   | Scope | Filename | Example |
   |---|---|---|
   | **Whole slice (the default cadence)** | `s<N>-slice-review.md` | `s3-slice-review.md` |
   | The slice's first task (design-setting) | `s<N>-task-<id>-review.md` | `s3-task-2.1-review.md` |
   | Several tasks in one pass | `s<N>-task-<id>+<id>-review.md` | `s3-task-2.2+2.4-review.md` |
   | Slice-wide, topic-scoped (architecture/NFR/parity) | `s<N>-<topic>-review.md` | `s1-nfr-review.md` |
   | End-of-plan | `final-review.md` | |

   **WHY the slice prefix:** task ids are unique only WITHIN a tasks file (`tasks-schema.yaml`), so S2's task `2.3` and S3's task `2.3` both exist. `task-2.3-review.md` is therefore ambiguous and two slices will fight over it. `s<N>` is the slice number of the tasks file that drove the review (`tasks-ADR-003-s3-…` → `s3`). Never invent your own disambiguator (`-s3-` as a suffix, `-first-pass`, `-rework`) — the prefix is the one rule.

   **Re-reviews APPEND a dated section to the same file** (`# Re-review — YYYY-MM-DD · …`) — never a new file. The file then carries several REVIEW RESULT signals; **the last one is the operative verdict**, and that is what the auto-chain routes on.

   Ad-hoc reviews with no feature folder fall back to `.claude/reviews/` (gitignored, local-only) and only need the `-review.md` suffix — no plan exists for them to collide with.

6. **State the REVIEW RESULT signal** (required on every review — the auto-chain routes on it):

   Critical or High findings exist:
   ```
   REVIEW RESULT: CHANGES REQUESTED
   Critical findings: N | High findings: M
   Developer must address all Critical and High findings before re-review.
   ```
   None:
   ```
   REVIEW RESULT: APPROVED
   The code is ready for user approval and commit.
   ```
   The literal token `REVIEW RESULT:` + the verdict is what routes — write it exactly. Decoration
   (`## REVIEW RESULT: APPROVED`, `**REVIEW RESULT: APPROVED**`) is fine, and stating it at the TOP
   as your headline is encouraged (`agent-interaction.md` — lead with the decision). `**Result:**
   APPROVED` or `VERDICT: CHANGES-ADVISED` do NOT route: six reviews shipped verdicts the auto-chain
   could not read, because a reader understands them and a grep does not.

7. **Add a `## Learnings` section** — recurring finding types, rule gaps, false-positive classes.
   The orchestrator routes it to dhruva; it is the only channel by which a review sharpens a rule.
   `none` is a valid answer; silence is not. A `Learnings:` inline line is equally acceptable.

## Before you save — the four elements the hook checks

All four sections are required by this contract — **you are the enforcement; no hook checks them.**
*(`check-review-file.py` was deleted 2026-07-29: it rejected all 25 sampled committed review files,
because `## Plan Defects` was added to the contract after they were written. A fail-closed guard
against a corpus that predates its own rule blocks the very re-review appends this skill requires.)*
Getting them right the first time costs nothing; a missing section costs the retro its signal.

- [ ] **Filename** carries the slice prefix — `s<N>-…-review.md` (or `final-review.md`)
- [ ] **`## Escaped Cases`** — `None` written explicitly if there are none
- [ ] **`## Plan Defects`** — `None` written explicitly if the plan held
- [ ] **`## Learnings`** — `none` written explicitly if there are none
- [ ] **`REVIEW RESULT: APPROVED|CHANGES REQUESTED`** — the literal token, once per pass

8. **Next step:** `developer` agent addresses findings via `/impl-review-points`
