---
name: intake-requirement
description: "Drive Phase A (Requirement) end-to-end — from a raw ask to approved stories: cheap module scan, candidate validation, capability grounding, 4-class triage, concept ideation (class 1), concept lock expressed as a draft PRD, PRD finalization (Gate 1a), user flows with their own ✓ checkpoint, stories (Gate 1b), dispatch. Phase A never reads code — depth belongs to the architect at Phase-B entry. Use when a requirement, PRD, change request, or feature idea arrives. Trigger aliases: analyze requirement, analyze PRD, understand requirement, new feature, intake."
argument-hint: "[requirement description, PRD path, or change request]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Skill, AskUserQuestion
---

# Intake Requirement — the Phase A driver

Intake: $ARGUMENTS

One driver, two sub-phases: **A1 · Concept** (divergent — thin intent to a locked concept) and
**A2 · Contract** (convergent — draft PRD → finalize → flows → stories → dispatch). The class
picked at triage selects the exit ramp; nothing skips triage. Load per-step detail from
`references/` only when that step runs.

## Pre-check
If the input already contains approved stories + ACs — skip to Step 10 (dispatch). An
already-finalized PRD — skip to Step 8 (flows). Partially complete input: fill only gaps.

## A1 · Concept

### Step 1 — Scan (cheap)
Read `.claude/rules/references/module-map.md` (one glance, 27 apps). Propose CANDIDATE modules
for this ask. No deep reading yet. If the map is missing/stale:
`python3 .claude/scripts/generate-module-map.py`.

### Step 2 — Validate candidates
`AskUserQuestion`: confirm / add / remove candidate modules. A 5-second veto beats a 5-minute
wrong read — an unvalidated list silently biases ideation toward the wrong neighbourhoods.

### Step 3 — Ground (conceptual depth, zero structural cost)
Read the CONFIRMED modules' capability layer only: app `CLAUDE.md`s, domain docs, existing
flows. Never code structure — the caller/parity audit is Step 7's job, paid once, on the
locked concept. Present understanding back; do not proceed unconfirmed.
When you present understanding back, also ask the **scope-completeness prompt**: "what else
should this capture, and is there any build-order or ownership preference?" This surfaces
CR-style additions NOW, before design hardens — a scope add caught here is a PRD edit; caught
post-design it's a halt + re-plan + respawn (both REF-001 change-requests arrived after design
had hardened). Every class passes through this step, so the prompt covers updates and refactors
too, not just new concepts.

### Step 4 — Triage (never skipped; the class picks the exit ramp)
Classify {1 new concept · 2 update · 3 bug fix · 4 refactor/debt} as a hypothesis; confirm via
`AskUserQuestion`. Full class definitions, the 1-vs-2 discriminator ("more than one plausible
product shape?"), and the bug-lane trap question ("wrong per spec, or spec changing?") live in
`references/triage-classes.md`.
- **Class 2** → record the confirmed-intent line (template in `references/intake-templates.md`)
  → jump to Step 8 (flows-patch on the canonical `flows.md`) → delta-stories at Step 9. No new
  PRD → no Gate 1a.
- **Class 3** → fill the bug card (repro · expected-vs-actual · blast-radius dirs) → exit to
  the dev loop. The trap question fires BEFORE exit.
- **Class 4** → parity framing → flows/stories existence check (present → patch mode; absent →
  mark bootstrap-required on the manifest; the bootstrap derives from the Step-0 parity
  inventory once it lands — see the Class-4 check in `references/triage-classes.md`) → jump to
  Step 10 (dispatch straight to Phase B — the architect boards via `/design-module`; its
  Step-0 parity inventory IS the depth). First design gate is the ADR; a required bootstrap
  (flows ✓, then stories ◆1b) closes before it.
- **Class 1** → continue.

### Step 5 — Ideate (class 1 only)
Propose 2–3 concept shapes — per shape: name · one-line JTBD · modules touched · one-line
trade-off (format in `references/concept-shapes.md`). WHAT-level only — the moment a shape
needs entity diagrams to compare, it has crossed into the architect's seat. User picks or
blends via `AskUserQuestion`. Guardrail: ideation ≠ invention — labeled options surfaced AT
the gate, never content smuggled past it.

### Step 6 — Lock & draft (one continuous move)
Announce: "Locking concept <X> — drafting the PRD." (Checkpoint, not a gate: the pick IS the
approval; reopens only via evidence.) Immediately invoke `/write-prd`, carrying the pick into
its **Chosen Concept · Rejected Shapes · Assumptions** sections. Constraints & modules stay
honest candidates — `UNCONFIRMED` with a named consequence where the capability layer and the
human can't answer; Phase B witnesses them with code evidence. The PRD is the sole record of
the pick — no parallel decision store.

═══ CONCEPT LOCKED — A2 · Contract begins (manager-owned end-to-end) ═══

## A2 · Contract

Phase A never reads code. The depth the old intake audit bought (impact analysis, T1–T6
escalation, the declared-modules scope fence) is the architect's FIRST move at Phase-B entry;
the fence is written AT the ADR (Gate 2). Premature depth is wasted depth — before the
architecture is known, code-level findings anchor the design instead of informing it.

After each step below, refresh the feature's **living review page**
(`references/review-page.md`) — the page is how the user comprehends what each gate approves.

### Step 7 — Finalize the PRD ◆ GATE 1a
Open Questions must be EMPTY (a PRD cannot finalize with open questions — bounce back instead;
`UNCONFIRMED — needs Phase B` entries with a named consequence are legal and travel on the
manifest). Present the PRD via the review page; explicit user approval flips
`Status: Draft → Final`. Rejection routes by kind: **scope wrong** → Step 5 (re-ideate with
the feedback) · **wording/detail** → iterate in place, re-present.

### Step 8 — User flows ✓ checkpoint
Invoke `/write-user-flows` on the finalized PRD → `<app>/docs/features/<slug>/flows.md`.
Render the journeys as diagrams on the review page and get the user's ✓. Flows DETERMINE
stories — a wrong journey caught here is one edit; caught at Gate 1b it's redone stories.
Class 2: PATCH the canonical `flows.md` (bootstrap it first if the legacy concept has none —
see `/write-user-stories` bootstrap rule).

### Step 9 — Stories ◆ GATE 1b
Invoke `/write-user-stories` — stories derive ONLY from the confirmed flows, each citing the
flow step it serves (class 2: delta-stories; their flows patch landed at Step 8, same pass).
Present for approval. Gate 1b is the phase exit (= the hub's Gate 1).

### Step 10 — Dispatch (pure handoff — the A→B hinge)
The manager's LAST act in Phase A: package the **dispatch manifest** (template in
`references/intake-templates.md` — PRD + flows + stories paths, Q&A digest, rejected shapes,
surviving UNCONFIRMEDs) and route by class with the full clarity cascade: class 1/2 → ADR
rail · class 4 → `/design-module`. What happens NEXT — the architect's deep read, the T1–T6
ledger (`.claude/rules/references/t-triggers.md`), the declared-modules fence at the ADR — is
Phase-B work, billed to Phase B. The architect asking the user anything this phase already
learned is a clarity-cascade failure.

## Rules
- Triage is never skipped; classes pick exit ramps.
- Deep effort only on what survived a cheap human veto (candidates → validate; shapes → pick;
  class → confirm).
- Up-classing is always a user question; down-classing is announce-and-execute.
- The sequence draft → finalize ◆1a → flows ✓ → stories ◆1b is invariant — no story derives
  from an unconfirmed flow.
- Phase A reads capability (CLAUDE.mds, docs), never code — depth is Phase B's opening move.
- No invention anywhere: thin input produces questions, never padded content.
