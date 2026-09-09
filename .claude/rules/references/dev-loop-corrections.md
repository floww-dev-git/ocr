# Design Correction Protocol — Load-on-Demand Reference

Loaded when a plan-artifact-is-wrong situation is detected mid-implementation (the HALT stub in
`dev-loop.md` points here). The spine keeps the 3-line trigger; the full protocol lives here so it
costs zero always-on context until a correction actually fires.

When the developer discovers during implementation that a planning artifact is wrong (e.g., a field is redundant, a user story has an incorrect assumption, an ADR decision is flawed), the following protocol applies.

## Who Does What

| Document | Owner | Updates it |
|---|---|---|
| PRD | `manager` | manager |
| User flows (flows.md) | `manager` | manager (via /write-user-flows, patch mode) |
| User stories | `manager` | manager |
| ADR | `architect` | architect |
| Task list | `architect` | architect |
| Feature context | `manager` | manager |
| Code / tests | `developer` | developer |

**The developer NEVER updates planning documents directly.** The developer's role is to detect and report the issue, not to fix documents outside their domain.

## Procedure

1. **Developer halts** — stops implementation on the affected task, does NOT proceed with a workaround
2. **Developer reports** — clearly states: (a) what the issue is, (b) which documents are affected, (c) the proposed correction
3. **Main session coordinates** — routes corrections to the owning agents:
   - If PRD or user stories need changes: route to `manager` with the developer's findings
   - If ADR or task list needs changes: route to `architect` with the developer's findings
   - If both need changes: route to `manager` first (requirements drive architecture), then `architect`
4. **User approves** — the corrected documents are presented for user approval before resuming
5. **Developer resumes** — implementation continues with the corrected plan as the new source of truth

## Severity Levels

- **Cosmetic** (typo in a user story, task wording unclear) — developer notes it, continues implementation, corrections are batched at end of task. No halt required.
- **Design** (redundant field, wrong entity relationship, missing edge case) — developer halts, protocol runs. This is the common case.
- **Structural** (wrong app ownership, fundamental architecture change needed) — developer halts, protocol runs, AND the architect must re-evaluate remaining tasks for cascading impact.

## Correction mechanics (tasks file)

- **Halt report names the exact task line** + a one-paragraph why.
- **The corrected document MUST state its impact on already-`[x]` tasks explicitly** — "rework needed: none" or the list of ticked tasks to redo. Silence on completed work is how corrected plans ship with a stale earlier task.
- **How much re-approval each severity needs:** Cosmetic — none, batch it. Design — show the user only the delta: which tasks changed, were added, or removed, plus any ordering knock-on. Structural — re-run Gate 3 for the tasks that remain (finished tasks keep their ticks; the tick-evidence hook protects them).
- **Re-validation is automatic** — the architect's edit to `tasks-ADR-*.yaml` fires the `check-tasks-yaml` PostToolUse hook (schema + tick-evidence + ordering + slice-naming); nobody re-runs it manually.
- **Single-writer** — the developer pauses ticking during a correction; the architect re-reads the tasks file fresh from disk before editing (never regenerates from context).

## Two Phase-B lanes

1. **Flow patch-lane** — the architect discovers a user flow is wrong. Route to the manager: fix `flows.md` (via `/write-user-flows`), update just the stories that cite the changed flow steps, show the user only those changes for a quick ✓ (not a full Gate-1 re-run), and the architect resumes. This stays cheap because every story names the flow steps it derives from — the blast radius is greppable.
2. **Reclassification lane** — a T1–T6 trip means the feature was classified wrong at intake (e.g. treated as a small update when it's really a new concept). No document patch fixes that. The manager runs the reclassification card (`intake-templates.md`), the user confirms (moving a feature UP a class is always the user's call), and the feature restarts Phase A ideation carrying the trip evidence. Everything derived under the old class is void.

For severity purposes: a flow patch counts as "Design"; a T-trip counts as "Structural" — plus it voids the classification.

## Anti-Patterns

- Developer silently working around a wrong plan instead of reporting it
- Developer updating PRD/ADR/user stories directly (violates ownership boundaries)
- Main session delegating all document updates to a single agent (violates ownership)
- Resuming implementation before corrected documents are approved
