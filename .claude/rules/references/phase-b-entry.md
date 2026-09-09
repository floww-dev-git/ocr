# Phase-B Entry — the architect's opening move

Phase A deliberately stays shallow — it names WHAT the feature does, not how the code works.
All the deep code-reading happens here, once, after the requirement is approved. Loaded by the
architect at Phase-B entry; pointed at from `architect.md` and `/design-module` — single home,
no copies.

## Lane 1 — class 1 (new concept) / class 2 (update)

Read in this order:
1. **The dispatch manifest** — the manager's handoff note: what the user answered, which shapes
   were rejected, which assumptions are still unconfirmed, and any T-trigger suspicions.
2. **The four PRD sections no other artifact carries:** Out-of-Scope, Constraints & Dependencies,
   Domain Terminology, Error Scenarios.
3. **`flows.md`, then the user stories.**
4. **The candidate apps' CLAUDE.mds, then the code itself** — for an unfamiliar app, read layers
   in order: models → storage interfaces → interactors → app_interfaces → adapters.

Check the PRD's assumptions and candidate modules against the actual code; settle the still-open
assumptions with evidence. Chase the manifest's T-suspicions FIRST — they are the likeliest
findings to change the plan.

## Lane 2 — class 4 (refactor) / module-scale class 1

`/design-module` Step-0 already inventories what the current code does — that inventory IS the
deep read (and IS the T5 parity check). Fill the ledger from it; don't do a second pass.

## The T1–T6 ledger

Run all six checks per `.claude/rules/references/t-triggers.md`. Write the ledger — always all
six rows, passes included — into `<slug>/design/phase-b-entry.md`. If a check
trips: stop designing and follow the Design Correction Protocol (`references/dev-loop-corrections.md`) — the architect
brings the evidence, the manager runs the reclassification card, the user confirms, and the
feature re-enters Phase A ideation.

## Extension-cost audit

If a touched module has an earlier ADR, compare that ADR's Extension Cost claim against what
THIS change actually costs ("new X = one class + one registry entry" — was it?). Report the
difference in the grounding digest; it feeds `/feature-retro` and sharpens the architect's
future estimates.

## Grounding ✓ (before ANY blueprint/ADR effort)

Send the user a short digest (through the orchestrator): which candidate modules were confirmed
in code · which PRD assumptions turned out false · the T1–T6 pass/trip results · which open
assumptions are now settled and which remain. This is announce-and-confirm, not a formal gate —
but it's the cheapest place in the pipeline to catch a wrong PRD: a false assumption caught here
costs a one-line PRD patch; caught at Gate 2 it throws away a finished design.

## Fence (pointer)

The declared-modules scope fence lives as a machine-readable header line in the ADR itself,
written by `/create-adr`'s save step — template in
`.claude/skills/intake-requirement/references/intake-templates.md`. `feature-context.md`
records only the ADR path.
