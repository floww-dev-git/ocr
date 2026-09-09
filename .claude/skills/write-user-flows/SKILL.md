---
name: write-user-flows
description: "Write user flows from a FINALIZED PRD — one journey per actor, diagram-first, happy + failure paths. A separate artifact (flows.md) with its own checkpoint: the user confirms the journeys BEFORE stories derive from them. Invoked by /intake-requirement Step 8 and directly via 'write user flows', 'plan the flows', 'user journeys'."
argument-hint: "[finalized PRD path]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write
---

# Write User Flows

Write flows for: $ARGUMENTS

Flows are the bridge between the PRD (WHAT & WHY) and the stories (testable behaviour). They get
their own artifact and their own checkpoint because they DETERMINE the stories — a wrong flow
approved late means every story derived from it is rework. Catching it here is the whole point.

## Input Contract

- A **finalized** PRD (`Status: Final`, Gate 1a closed) — never a draft; every draft edit would
  invalidate the journeys derived from it.
- If the PRD is a draft or has unresolved Open Questions, stop and bounce back.

## The Artifact

Save to `<owning_app>/docs/features/<slug>/flows.md` — the single canonical home for this
feature's flows (PRDs do not carry flows; stories cite these steps).

One flow per actor journey, **diagram-first** — flows have shape, and prose hides shape:

```markdown
## F1 · <Actor> — <journey name>

Actor → step 1 (does X) → system responds Y → step 2 … → outcome

1. <Actor> does X → observes Y
2. ...

### Failure paths
- F1.a — at step 2, <what goes wrong> → <what the actor observes>

### Interruption / concurrency edges
- F1.i — <mid-flow interruption> → <resumability expectation>
```

- Number flows (F1, F2…) and steps — stories will cite `F1 step 3` verbatim.
- Cover: happy path + every failure path from the PRD's Error Scenarios + mid-flow
  interruption/concurrency edges the journey exposes.
- **Altitude:** what the actor does and observes — never screens, storage, or implementation.
  Hints die here.

## No-Invention Rule

Flows are DERIVED from the PRD's actors, scope, and error scenarios plus the human's answers.
A journey the PRD doesn't imply and the user didn't describe is a question, never a flow. Thin
input produces questions about the journey back at the human — not padded steps.

## The Checkpoint (not a formal gate)

Present the flows — on the living review page they render as actual diagrams — and get the
user's confirmation. **Stories may not derive until the journeys are confirmed.** A flow
correction after stories exist means redone stories; that rework is what this beat prevents.

## Class-2 Updates

No new flows doc — PATCH the existing `flows.md` (delta), bootstrapping it from current
behavior first if it doesn't exist (see `/write-user-stories` bootstrap rule). The patch and
the delta-stories land in the same Gate-1b pass.
