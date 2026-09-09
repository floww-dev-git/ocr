---
name: process-tasks-list
description: Execute and manage a task list — one sub-task at a time with user approval
argument-hint: "[path to task list file]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Process Task List

Process: $ARGUMENTS

## Protocol

- **Auto-advance task-to-task** — there is NO per-sub-task user-approval gate. The pipeline owns progress gating: independent review on the slice's first task and once per slice after its closer (dev-loop Review Per Slice, Not Per Task), and ONE push gate at end-of-plan (dev-loop Commit Frequently, Gate Once). On completing a sub-task, proceed to the next.
- **On sub-task completion:**
  1. Mark as `[x]` in the task file — the tick-evidence hook verifies the ✔ artifact exists on disk
  2. Run `pytest` for the affected test file(s)
  3. If models changed: run `python manage.py makemigrations` + `migrate`
  4. When ALL sub-tasks under a parent are `[x]`: mark parent as `[x]`
  5. Update `feature-context.md`'s "Active task" line by QUOTING the next task's exact line text from the tasks file (not just a number) — a cold session greps one string and lands in both files unambiguously
  6. **Commit this sub-task locally NOW** — automatic and announced ("Committed: `<subject>` — N files"), never asked, per `.claude/rules/dev-loop.md` (Commit Frequently, Gate Once). Never push. Then proceed.
- **Honour the tasks file's Carried Flags footer** — surface each flag at its named task's report.
- **PUSH fires once at end-of-plan** — after the final sub-task passes and its slice review is clean, present the commit series (one line per task) + test report for the single push approval. Mid-plan exceptions: user says "push now", or the safety valve (10+ tasks committed-but-unpushed) suggests an interim push.
- **During a Design-Correction halt, PAUSE all ticking** until the corrected tasks file returns (single-writer discipline; re-read the file fresh from disk after the correction before resuming).

## Maintenance

- Add new tasks as they emerge during implementation
- Keep "Relevant Files" section accurate
- Follow @.claude/rules/ for all code standards
