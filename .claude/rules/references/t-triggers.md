# T1–T6 Escalation Triggers — the architect's Phase-B entry checks

Loaded by the `architect` at **Phase-B entry** — the first deep code read after the dispatch
manifest arrives. Phase A classified the ask at capability altitude; these six checks are how
the code gets to falsify that classification before any design hardens on it. The escalation
*protocol* on a trip runs back through the manager via the **Design Correction Protocol**
(`references/dev-loop-corrections.md`) — the architect produces the evidence, it never reclassifies unilaterally.
All six are facts the entry read already computes — the ledger is free.

## The ledger format

One row per trigger, ALWAYS all six (a pass row proves the check ran; an absent row proves
nothing). The ledger lives in `<slug>/design/phase-b-entry.md` — the architect's first Phase-B
artifact (the ADR deliberately bans process-evidence sections, and feature-context stays
a lean resume pointer). A user-overruled trip surfaces in the ADR inline with the affected decision, as
"Assumes X (Tn overruled, see ledger). If not true, Y." One line per trigger:

```markdown
| T | pass/TRIP | evidence (one line, file refs) |
```

## Definitions & check procedures

### T1 — Homing failure
**Trip:** the new behaviour homes on NO existing entity without inventing a synonym.
**Check:** for each new behaviour in the intent/PRD, name the existing entity that would own it
(read the owning app's models + CLAUDE.md). If the only candidates require a new domain noun or
a synonym for an existing one (`clean-code.md` bans invented synonyms), T1 trips.

### T2 — Rule of three
**Trip:** the update would create the 3rd+ copy of the same shape.
**Check:** grep for the pattern the update replicates (similar handler/checker/node shapes).
Two existing copies + this one = trip. Cite both existing copies by path.

### T3 — Edge novelty
**Trip:** a new cross-app integration edge, or a would-be dependency cycle.
**Check:** diff the change's edges against the current app dependency map
(`clean-architecture.md`). Any edge that doesn't exist today, or whose addition closes a cycle,
trips. Direction must also pass the stability check (SDP) — a wrong-direction edge is a trip
even between already-connected apps.

### T4 — Unabsorbed axis
**Trip:** the host has no extension point AND the change axis is confirmed recurring.
**Check:** does the host module have a registry/strategy/plug-in surface that absorbs this class
of change with zero core edits? If core edits are required AND the intake Q&A confirmed the axis
recurs (never speculate the recurrence yourself), T4 trips.

### T5 — Parity gap
**Trip:** the request describes well under the live behaviour set (canonical case REF-001: the
requirement covered ~60% and missed 14 behaviours).
**Check:** inventory what the touched code paths actually do today (callers, side effects,
config branches). If the intent/PRD is silent on a material fraction of live behaviour, T5
trips — the gap IS the evidence; list the uncovered behaviours.
**Config-flag corollary:** a story that adds a config flag/field but traces only ONE edge (write
without read, or read without write) is a parity gap in miniature — an unreachable or unread flag.
The authoring-time guard lives in `write-user-stories/SKILL.md` ("A Capability Assertion Is Not an
Acceptance Criterion"); at Phase-B entry, confirm both edges exist against live code.

### T6 — Contract break
**Trip:** API/DTO breakage for external consumers — user-visible.
**Check:** would the change alter/remove GraphQL fields, DTO shapes crossing app_interfaces, or
ext_client/floww_cli schemas? Additive is safe; removal/retype/rename trips (see architect.md
API Evolution: `deprecation_reason` + 2 release cycles, unions expand safely).

## On a trip

Halt design work and bounce via the **Design Correction Protocol** (`references/dev-loop-corrections.md`): report
`T-TRIGGERED (Tn — evidence)` to the orchestrator; the manager runs the reclassification card
(template in `intake-requirement/references/intake-templates.md`) → **user confirms**
(up-classing is always a question) → the feature re-enters Phase A at ideation WITH the
evidence. One-way, once, never after tasks are cut. A user overrule is recorded with the
T-evidence and work proceeds at explicit, logged risk.
