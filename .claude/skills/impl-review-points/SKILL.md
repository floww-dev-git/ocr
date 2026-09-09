---
name: impl-review-points
description: Address code review findings end-to-end without per-point approval gates — fix all Critical/High findings, self-review, and hand back for re-review. Auto-invoked when the reviewer returns CHANGES REQUESTED; also for user-pasted review comments or PR feedback.
argument-hint: "[review findings, comments, or PR link]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Implement Review Points

Address: $ARGUMENTS

Auto-continue applies (`agent-delegation.md`): review findings feed straight into fixes —
never ask "should I fix these?" and never pause for approval between points. The fix cycle
shares the original commit gate; no new gates here.

## Process

1. **Triage all points up front** — group by file; order Critical → High → Medium → Low.
   Batch any genuine clarifications into ONE message (per `consent-granularity.md`) — only for
   findings that are ambiguous or look wrong, not as a routine step.
2. **Fix Critical and High findings** — all of them, one logical unit at a time. Medium/Low:
   fix now if cheap, otherwise note for follow-up in the report-back.
3. **Halt only for design-level findings** — if a finding implies a planning artifact (PRD,
   story, ADR, task) is wrong, do NOT work around it: route through the Design Correction
   Protocol (`dev-loop.md`).
4. **Re-run the affected tests** after each logical unit; if a fix changes behaviour, update
   the task's `Cases:`-derived tests to match the corrected behaviour — never delete them.
5. **Self-review** — run `/self-review-checklist` against the changed files (not just a
   clean-code skim).
6. **Report back for re-review** — list each finding → fix applied (file:line) → test evidence.
   The orchestrator re-invokes the reviewer automatically.
