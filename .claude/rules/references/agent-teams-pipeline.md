# Agent Teams & Pipeline Reference

This file contains detailed templates and tables for agent teams and pipeline auto-chaining.
Referenced by `agent-delegation.md` and `dev-loop.md` rules. Loaded on-demand, not always-on.

## Who Drives the Auto-Chain: Manager vs Task-Coordinator

The auto-chain has two kinds of rows: **gate rows** (a user approval surfaces) and **between-gate rows** (the dev/review/fix/tick/commit loop). The manager owns the gate rows — always, at depth-0. The between-gate rows can be driven two ways:

- **Manager drives directly** (default for a single small slice) — the manager spawns developer/reviewer/tester itself and runs the between-gate table.
- **Manager delegates the slice to a `task-coordinator`** (preferred for a slice with real inner-loop volume) — the manager spawns ONE ephemeral coordinator per slice; the coordinator becomes the **driver of the between-gate rows** for that slice (spawns app-fenced devs, runs the first-task + whole-slice reviews, routes findings, ticks, per-task commits), absorbs the full task firehose + idle pings, and returns a compact summary. The manager still owns every gate row. The coordinator bubbles UP at the push gate / a blocker / a design correction; it never presents a gate itself. See `.claude/agents/task-coordinator.md`.

In the tables below, "Main session does" means **whoever is driving that row** — the manager for gate rows, the task-coordinator for between-gate rows when one is in play. **Nested-team caveat:** a task-coordinator is itself a subagent, so it cannot spawn an Agent Team (rule 6). It achieves worker parallelism via multiple concurrent `Agent` **subagent** calls (app-fenced), not the team primitive; the Agent-Team rows below apply only when the **manager** drives directly.

## Blocking vs Background Spawns — read BEFORE the auto-chain table

### WHY (verified against official docs 2026-07-29, Claude Code v2.1.220)
**Claude Code v2.1.198 flipped the default: an `Agent` call that omits `run_in_background` now
launches a BACKGROUND subagent and hands control straight back. Before v2.1.198 the same call ran
SYNCHRONOUSLY.** The auto-chain table below was written under the old default — every row reads
"X returns → immediately invoke Y", which assumes the spawn blocks until it produces a result.
It no longer does unless you say so. Symptoms when this is left implicit: the chain advances
before the previous step finished, agents look "stalled" (they are backgrounded, pinging idle out
of band), and the driver re-spawns work that was already in flight.
Source: https://code.claude.com/docs/en/agent-sdk/subagents

### The rule
- **Every pipeline handoff in the auto-chain table below BLOCKS. Pass `run_in_background: false`
  explicitly.** If the next row needs this row's result — and in a sequential chain it always
  does — the spawn is synchronous. Never rely on the default.
- **Background is for work whose deliverable is a FILE, not a return value**: research passes,
  audits, independent parallel fan-out. Poll for the file; never wait on the final message
  (`Shared-File Discipline` rule 3).
- **Parallel fan-out still blocks at the JOIN.** Spawn N independent workers in one message, then
  wait for all N before advancing the chain. Concurrency is about the workers being parallel with
  each other, not about the driver racing ahead of them.
- **An idle ping is not a completion signal.** Check disk (git log, tick counts, the report file)
  before concluding anything finished. A slow worker and a finished one look identical from a ping.

| Spawn kind | `run_in_background` | Done signal |
|---|---|---|
| Auto-chain handoff (manager → architect → developer → reviewer …) | `false` | the Agent result |
| Fix-cycle re-spawn after review findings | `false` | the Agent result |
| Research / audit / config investigation | `true` | the report FILE exists |
| Parallel app-fenced workers | `true`, joined before advancing | all report files exist |

## Pipeline Auto-Chain Rules

Every "invoke"/"spawn" row below is a **blocking** spawn (`run_in_background: false`) unless the
row itself says otherwise — see the section above.

| When this happens | Main session does |
|---|---|
| Manager returns approved user stories | Immediately invoke `architect` with the user stories |
| Architect returns ADR + user approves (Gate 2) | Immediately invoke `architect` with `/task-breakdown` (ADR + the stories it serves) |
| Architect returns the task breakdown + user approves (Gate 3) | Immediately invoke `developer` to begin executing tasks |
| Developer completes the slice's **FIRST** task (the design-setting one — interactor + the contracts it drives out) | Invoke `reviewer` at `model: sonnet` immediately — cascade risk concentrates here (`dev-loop.md` Review Per Slice, Not Per Task) |
| Developer completes any **LATER** task in a slice (code + tests + self-review + integrate + automatic local commit) | Advance the feature-context Active pointer + phase (status strip `[S1 · 25/30 · pace · ≈ETA to gate]` via `/feature-status`); auto-advance to next task — **NO review, NO user gate between tasks** (see `dev-loop.md` Commit Frequently, Gate Once + Review Per Slice) |
| Plan reaches a slice's integration-suite closer sub-task | Invoke `tester` with the slice's stories + ACs + flows + ADR § (the closer's `Cases:` line = one per AC, pre-approved) |
| **Slice's integration closer passes** | Invoke `reviewer` at `model: sonnet` over the WHOLE slice → saves `s<N>-slice-review.md`. This is the cadence's main event — the only altitude that sees cross-file duplication/drift |
| Slice touches an engine boundary, a novel architecture surface, or has an NFR/parity dimension | Invoke `reviewer` at `model: opus` with the focus briefing → `s<N>-<topic>-review.md`. Tier follows review KIND, not path sensitivity |
| Final task's INTEGRATE passes (before the push gate) | `tester` finalizes `<app>/docs/features/<slug>/test-report.md` (AC-traceability matrix + coverage) — rides into the push-gate presentation |
| Reviewer returns Critical/High findings (first-task or slice review) | Immediately invoke `developer` with findings via `/impl-review-points` |
| Developer fixes review findings | Immediately re-invoke `reviewer` for re-review — re-review reads its prior review + the hunks since, NOT every file again |
| Reviewer returns clean on the first-task review | Developer makes the task's local commit (auto); auto-advance to next task |
| Reviewer returns clean on a slice review + more slices remain | Auto-advance to the next slice — no user gate |
| Reviewer returns clean on the FINAL slice + sensitive paths touched* | ⏸ Security auto-review DISABLED (2026-07-10) — present the commit series + test report for PUSH approval -> **GATE** (manually invoke `@security` if a change warrants it) |
| Reviewer returns clean on the FINAL slice + no sensitive paths | Present the commit series + test report for PUSH approval -> **GATE** |
| Security agent returns clean *(manual @security only — auto-review disabled 2026-07-10)* | Present the commit series + test report for PUSH approval -> **GATE** |
| Security agent returns findings *(manual @security only)* | Invoke `developer` with findings, then re-invoke `security` |
| Single-task work (1 task on plan, ad-hoc fix, Sentry) completes review clean | Local commit (auto), then present for PUSH approval -> **GATE** |
| Plan accumulates 10+ tasks committed-but-unpushed | Suggest an interim push (work is already crash-safe locally) |
| User says "push now" mid-plan | Push the committed-so-far series, then resume the plan |
| User approves the push | Invoke `developer` to push the series (per-task commits already made) |
| Push complete | Invoke `manager` with `/promote-to-envs` to ask which env branches need PRs -> **GATE (single checklist question)** |
| User replies `none` | Skill ends. Return dev to `feature/<name>`. |
| User selects one or more of `alpha`/`beta`/`gamma`/`tg-bn-gamma`/`tg-bn-uat` | Invoke `developer` with the resolved target list to run the `/promote-to-envs` mechanical sequence per target |
| Developer finishes all targets | Present PR table (target, PR id, URL) + return dev to `feature/<name>` (no more gates) |

\* **Sensitive paths**: `iam/`, `payments_engine/`, `ib_payments/`, `bps/`, `tdr/`, any new external integration adapter, or files touching auth logic.

\*\* **Promote-to-envs gate**: the env-checklist prompt is the ONLY question between push confirmation and PRs being opened. Sub-decisions during the per-target mechanics (conflict direction, re-stage after black, companion back-fill, return-to-branch) are announce-and-execute per `consent-granularity.md`. `tg-bn-prod` is intentionally excluded from the checklist — prod promotion is a separate release-management step.

## Approval Gates (pipeline pauses ONLY here)

1. After user stories (manager)
2. After ADR (architect)
3. After implementation plan (architect, /task-breakdown)
4. After clean review on the FINAL slice of the plan (reviewer) — security auto-review disabled 2026-07-10
5. Before PUSH (single gate — per-task local commits are automatic; the gate reviews the commit series + test report and approves the push, once per plan)
6. After push — env-promotion checklist (single question, resolved in one reply)

**Reviews still happen** (gate 4 fires on the slice's first task and on each slice review), but they are NOT user-facing gates when clean — only Critical/High findings pause the loop. The user sees ONE push gate per plan; per-task commits are automatic and announced. Later tasks commit before their slice review — safe by construction, because those commits are local and the push gate sits *behind* the slice review (`dev-loop.md` Review Per Slice, Not Per Task).

## Agent Teams — When to Use

| Stage | Default | Use Agent Team When |
|---|---|---|
| Manager | Subagent | Never — conversational |
| Architect | Subagent | Never — one coherent design |
| Developer | Subagent | 4+ tasks with NO dependencies, different files, different apps |
| Review | Subagent | 3+ distinct review concerns each need a seat (novelty, not file count — see Review Team) |
| Fix cycle | Subagent | Never — small, sequential |
| Commit/Push | Subagent | Never — single operation |

## Developer Team

Spawn ONLY when ALL conditions met:
1. **4+ tasks** with **zero dependencies**
2. Tasks touch **different files**
3. Tasks span **different apps**

Common triggers: multiple configio handlers, multiple workflow nodes, multiple independent GraphQL queries, multi-app isolated changes.

```
Team size: min(independent_task_count / 2, 4) teammates
  — 4-5 tasks -> 2 teammates
  — 6-7 tasks -> 3 teammates
  — 8+ tasks  -> 4 teammates (max)

Each teammate receives:
  - Developer persona + memory
  - Assigned tasks with explicit file boundaries
  - "Do NOT touch files outside your assignment. Message teammates if needed."
  - "Run self-review-checklist after completing all tasks."
```

Exit criteria per teammate: all tasks done, tests passing, self-review passed, ruff passing, no files outside boundary.

## Review Team

Scale review seats to **NOVELTY (distinct concerns), not raw file count.** Count the distinct
review concerns in the changeset — architecture · clean-code · test-coverage · security · a
genuinely novel pattern — not the files. **N near-identical files are ONE reviewer, not N**: 10
pattern-guards cut from the same template = one seat that reviews the pattern once and spot-checks
the rest. A 12-file changeset that is one repeated shape needs a single reviewer subagent; a
4-file changeset touching auth + a new engine + a migration may warrant a team. Rule of thumb:
spawn a team only when **3+ distinct concerns** each need a dedicated seat; otherwise a single
reviewer subagent. Smaller scopes also survive flaky infra better — less re-run exposure per seat.

**Non-sensitive:** 2 teammates (Architecture+CleanCode, TestCoverage+EdgeCases)
**Sensitive:** 3 teammates (above + Security with OWASP focus)

```
Each teammate receives:
  - Reviewer persona + memory (or security.md for Reviewer 3)
  - Full list of changed files + specific focus area
  - "Output structured findings (Critical/High/Medium/Low). End with APPROVED or CHANGES REQUESTED."
```

The TestCoverage+EdgeCases seat is a **reviewer** teammate — never the tester. Reviewing
tests requires fresh eyes (the tester authored them) and the findings/severity/REVIEW-RESULT
discipline the authoring persona lacks. For extra test depth, give this teammate the `testing.md`
gotchas (bare-attribute stub trap, factory-vs-MagicMock, foreign-scope `assert_not_called`,
contract-test false positives) as its focus briefing — depth lives in the briefing, not a persona swap.

**Consolidation-save (required):** after the team's findings are merged, the orchestrator saves the
consolidated review — all findings + the `## Escaped Cases` section + the REVIEW RESULT signal — to
`<owning_app>/docs/features/<slug>/reviews/<scope>-review.md` (re-reviews append a dated section).
Single-reviewer runs save their own report to the same folder (see `/review-pr` step 5). Reviews are
feature artifacts — tracked, travelling with the branch; `/feature-retro` greps the folder. An
unsaved review is invisible to the retro loop.

## Agent Teams + Auto-Chain (extended)

| When this happens | Main session does |
|---|---|
| Plan approved + 4+ independent tasks | Spawn developer **team** |
| Plan approved + sequential tasks | Invoke developer **subagent** |
| Slice complete + 3+ distinct concerns + no sensitive paths | Spawn review **team** (2) |
| Slice complete + 3+ distinct concerns + sensitive paths | Spawn review **team** (3) |
| Slice complete + fewer distinct concerns (incl. N near-identical files) | Invoke reviewer/security **subagent** |
| Review team returns Critical/High | Invoke developer **subagent** with all findings |
| Review team returns clean | Present the commit series for PUSH approval -> **GATE** |

## Agent Team Rules

1. One team at a time — clean up before spawning next
2. Separate teams for dev and review — never mix
3. File ownership — each dev teammate owns specific files, no overlap
4. Max team size — 4 dev, 3 review
5. Fallback — if Agent Teams unavailable, fall back to subagent silently
6. No nested teams — teammates cannot spawn their own teams

## Clarity Cascade Template

When delegating to an agent, wire it to its context — **pass PATHS, not payloads.** A spawned
agent auto-loads its own persona and can Read any file on demand; pasting whole ADRs, studies, or
personas inline re-pays the token COUNT on every spawn for context the agent could pull itself.
Paste ONLY the decision-delta the agent can't derive from a file — the confirmed scope facts, the
rejected shapes, the specific open call. Everything else is a path.

```
<agent-memory>
{path to .claude/agent-memory/<name>/MEMORY.md, if it exists — the agent reads it}
</agent-memory>

<prior-context>
{the decision-DELTA from previous pipeline agents — manager's confirmed scope for architect,
architect's chosen trade-off for developer, the specific finding for the fixer. A few lines, not
a transcript. Cite the artifact PATH (ADR, stories, study) for anything the agent reads in full.}
</prior-context>

<task>
{the actual request + the file paths that scope it}
</task>
```

The persona loads from the agent definition — don't paste it. If memory doesn't exist, skip
`<agent-memory>`. If no prior context, skip `<prior-context>`. After the agent completes, if it
reported issues or corrections — invoke Dhruva to update memory/rules.

## Shared-File Discipline (Single-Writer)

### WHY
A background dev agent rewrote a tasks file from its stale context and wiped every tick another session had made (real incident, 2026-07-02). Two background agents also stranded their reports in final messages that never surfaced.

### Rules
1. **One writer per shared file at a time** — tasks files, `feature-context.md`, and memory files have a single owner while a plan is in flight; other agents read, never write.
2. **Re-read before every edit** — before editing a shared file, an agent MUST re-read it fresh from disk and apply a targeted edit. NEVER regenerate a shared file from conversation context — your context is stale the moment another agent touches the file.
3. **Background agents report to files** — any agent spawned in the background writes its deliverable to a file (report path stated in its prompt) — a final message may never surface. The orchestrator polls for the file, not the message.
4. **The git index counts as a shared file — commit with `git commit --only <paths>`.** Lanes sharing one checkout share one index, and a plain `git commit` commits everything staged, sweeping another lane's work into your commit. `--only` scopes the commit to the paths you name. Rule 2 has no equivalent here — you cannot "re-read the index fresh" and recover the other lane's intent, so the fence has to be on the write. *(Near-miss on relieve-v2, caught only because the formatting hook aborted the commit first.)*
5. Mechanical backstop: the tick-evidence check (`check-tasks-yaml.py` → `tasks_lib.check_tick_evidence`) blocks tick-wipes/false ticks on the YAML tasks files, but the discipline applies to ALL shared files. *(The legacy-markdown guards `check-tick-evidence.py` and `check-task-ordering.py` were deleted 2026-07-29 — YAML is the single tasks format, so they guarded a retired shape.)* Prefer `tasks.py tick/untick` — it re-reads, revalidates, and is fail-closed.
