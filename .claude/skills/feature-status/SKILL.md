---
name: feature-status
description: Show the status of active features — SDLC phase, % complete (raw + size-weighted), pace from per-task commit timestamps, an evidence-based ETA, blockers, and the next gate. Use when the user says "show status", "status", "feature dashboard", "% done", "ETA", "how far along", "what's left".
disable-model-invocation: false
allowed-tools: Read, Bash, Glob, Grep
---

# Feature Status Dashboard

## Process

1. **Discover active features** — glob `*/docs/features/*/feature-context.md` (the canonical
   home; one per feature, tracked). Worktrees (`git worktree list`) are a secondary source for
   parallel work. The current branch names the ACTIVE feature.

2. **Per feature, compute — never estimate what can be counted:**
   - **Phase** — from feature-context's phase checkboxes + any DCP/HALT banner in its tasks files.
   - **Progress %** — run `python3 .claude/scripts/tasks.py progress <file>` per
     `tasks/tasks-ADR-*.yaml`: it returns raw (`done` ÷ total tasks) and size-weighted
     (S=1 · M=2 · L=4). Report BOTH: `14/23 tasks (61%) · weighted 55%`.
   - **Pace** — per-task commits carry timestamps (Commit Frequently, Gate Once):
     `git log --since=<plan start> --pretty='%ci %s'` on the feature branch, count task commits
     per working day. Fewer than 3 task commits → "no pace data yet", and say so.
   - **ETA (estimate, always labeled, always with its basis)** — remaining weighted units ÷ pace,
     expressed in working days AND remaining task counts: `≈ 2.5 working days at current pace
     (9 tasks: 4S 4M 1L)`. NEVER emit a bare date without the pace basis; never fabricate an ETA
     when pace data is missing — "9 tasks remain (4S 4M 1L); no pace data yet" is the honest form.
   - **Blockers** — DCP banners, carried flags due, BLOCKED scout findings, waiting-on-user gates.
   - **Open-task reconciliation (required when a slice or step is closing)** — list every task
     still `status: todo` in a slice whose review came back clean, each with its reason and owner.
     A `%`-done figure and a clean slice review both stay silent about a task someone parked and
     nobody unparked, so this line is the only place it surfaces. Emit `open: none` when there are
     none — the empty answer is what proves the check ran. Also surface
     `tasks.py validate`'s warnings here, not just its `OK`/fail verdict: a prose-blocker warning
     means a task is waiting on work the queue orders after it.
   - **Next gate** — the nearest ◆ (flows ✓ / 1a / 1b / 2 / 3 / push / promote).

3. **Present the dashboard**

   ```
   Active Features
   ─────────────────────────────────────────────────────────────────────────
   workflow-engine-consolidation   Build · S1 (slice 1/7)        ◆4 push gate next
     ████████░░░░ 14/23 tasks (61%) · weighted 55%
     pace 5 tasks/day → ≈ 2 working days for S1   ⚠ CR-2 (DCP) in progress
   other-feature                   Design · Gate 2 next          no pace data yet
   ─────────────────────────────────────────────────────────────────────────
   ```

4. **Flag issues** — no task commits for 3+ days · blocked with no unblock action · all tasks
   ticked but push gate never presented · weighted % far below raw % (the hard tasks are the
   ones left — say so).

5. **Recommend** what to work on next: priority (from feature-context) → momentum (closest to a
   gate) → unblocked status.

## Caching — recompute on state change, not per prompt

The computed strip is cacheable. A bare "status?" with **no state change since the last
computation** replays the cached strip — do NOT re-glob every `tasks-ADR-*.yaml` and re-walk `git log`.
Recompute (the full Process above) only when state actually moved: a task tick, a passed gate, a
new commit, a changed blocker. The counting is cheap but not free at high frequency, and a
same-state answer that differs from the last one is confusing, not helpful. Multi-feature
dashboards (the full table) always recompute — the cache is for the single active-feature strip.

## Honesty rules

- % is COUNTED from tick marks, never guessed. Pace is COUNTED from commit timestamps.
- An ETA is an extrapolation and is presented as one — with its basis, in working days,
  recomputed every report. Slippage against the last report is stated, not hidden.
- Scope-change caveat: an ETA is valid only for the CURRENT plan; a DCP correction or added
  slice resets it (say "ETA resets pending CR-N" rather than pretending continuity).
