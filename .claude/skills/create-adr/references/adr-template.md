# ADR Template — filled by /create-adr, never hand-derived

Two shapes. Pick by change size (skill step 3). **Default to lean.** Plain language and the
banned-words list apply to both (see SKILL.md).

`workflow_engine/docs/features/workflow-engine-consolidation/adrs/ADR-001-s1-workflow-structure-and-reads.md`
is the gold-standard LEAN example — read it before writing a lean ADR, especially its `## Decisions`
section: clean bullets grouped under `### N · theme`, each `- <plain statement> (Dn)`, one `★ your
call` fork, and NOT a single `— instead of X` tail (the alternatives live in its narrative).

---

## Shape 1 — LEAN (the default)

For a small or medium change on a pattern the codebase already has. Drop any section it doesn't
need. Keep the header fence line exactly as shown — a hook parses `**Declared modules:**`.

```markdown
# ADR-NNN: <plain title — what this change does, in everyday words>
Status: <Proposed | Accepted (Gate 2, <date>)>
**Declared modules:** `dir/a`, `dir/b`
<optional pointer line — include only the ones that exist:>
Blueprint: <path>  ·  Implementation plan: <added by /task-breakdown>  ·  Stories: <path>

## Problem
What's broken today, in 2-4 plain lines — the drift, the duplicate logic, the missing check, the
pain this change removes. State it BEFORE any solution. Even the smallest ADR opens here: a reader
must see what hurts before what we build.

## What we add
A plain list of the things this change adds. One line each. No jargon.

## Behaviour
What each thing does, in short sentences — the happy path, then the edges and the "runs last /
overrides" rules. This is where the WHY lives (once).

## How it works
A DIAGRAM first, then a line or two. Show, then tell.
```
 input
   │
 branch? ── a ──→ …
   │ b
   └──────→ …
```

## Notes
Only what's needed: config storage, the errors raised and who raises them, any ports defined.
Skip the section if there is nothing to add.

## NFR notes
OPT-IN, and NON-FUNCTIONAL ONLY — "how WELL", never "what the system does". Include only genuine
non-functional concerns: performance, caching, concurrency, resource use, availability,
observability, migration safety. A behaviour a user story could assert with a Given/When/Then (a
foreign-account read returns empty · a port fails closed on ownership · no existence leak) is a
FUNCTIONAL or security AC — the WHAT — so it belongs in a user STORY (manager-owned), NOT here;
flag it back to the manager. A small change on an established pattern usually has NO NFR concerns —
then DROP this whole section. Do not fill it to look complete: an NFR section padded for form's
sake is the boilerplate this skill exists to prevent (YAGNI). When it earns a place, render it like
the Decisions list — clean grouped bullets, ONE plain line per concern, grouped by disposition.
Never dense paragraphs. Drop any group with no entry.

### Designed (must-have)
- <the concern> — what was designed, and why it's a must (one plain line).

### Deferred (with reason)
- <the concern> — what's deferred, and the one-line reason it can wait.

### Non-issues (with reason)
- <the concern> — why it doesn't apply to this change (one plain line).

## Decisions
The 30-second scan — a clean index of choices, NOT the argument. Each bullet is one plain statement
+ a trailing `(Dn)` id + any `★ your call` marker. NO `— instead of X` tail: the rejected
alternative and the reasoning both live in the narrative above (Problem / Behaviour / How it works /
Notes), said once (Principles #4–5). Render by count:

**A handful (≤5): a flat bullet list.**

- <plain decision statement>  (D1)
- <plain decision statement>  (D2)  ★ your call

**Many (6+): group under plain `### N · theme` headings, clean bullets per theme.** The grouping is
what keeps many decisions scannable — it serves the 30-second scan, doesn't contradict it. A short
line above the groups may flag which decisions are `★ your call` and name the recommended option.
Mark a user-facing fork (scope · visible behaviour · business consequence) `★ your call`; technical
picks carry no marker.

### 1 · <plain theme name>
- <plain, jargon-free choice>  (D1)
- <plain, jargon-free choice>  (D2)  ★ your call

The alternative each choice beat is NOT on the bullet — it is in the narrative above, recorded once
with the reasoning (Principles #4–5). A bullet that carries a `— instead of X` tail is the old
format and must be rewritten.
```

---

## Shape 2 — FULL

For a large or novel design (a new engine/app, a cross-app boundary being invented, real NFR
forces to weigh). Same header + fence line. Same plain language.

```markdown
# ADR-NNN: <plain title>
**Status:** Proposed | Accepted | Implemented | Superseded (whole or per-decision: "D2 → ADR-YYY·D1")
**Declared modules:** `dir/a`, `dir/b`
**Date:** <date> · **Blueprint:** <path | none> · **Implementation plan:** <added by /task-breakdown> · **Stories:** <path>

## 1. Context & Problem
Business drivers, what triggered this (1-3 short paragraphs).
### Forces & Constraints
| F# | Dimension | Constraint | Source |
(source-cited or cut — no invented latency numbers, no "scales to millions")

## 2. Design Overview
ONE control-flow diagram (sync/async boundaries, doors, failure paths) + one paragraph.

## 3. Modules & Ownership
Who owns what; deviations only.
▸ D1 (dependency-direction calls)

## 4. Entities & Data Design
Lifecycle narrative per entity (born → transitions → ends; never a column dump); queried-field
column-vs-metadata classification.
▸ Dn

## 5. Interactor Architecture
COMMITTED, not preliminary. One named door per use case; per door: trigger → step narrative
(validate → transform → persist → side effects, at interactors.md altitude) → the collaborator
seam each step demands (engine / port / storage).
### Core Decision Logic  (CONDITIONAL — only when a central decider exists: decision pipeline diagram)
▸ Dn (boundary / composition calls)
Open items: code-contingent confirmations ONLY, each assigned to the breakdown.

## 6. Infrastructure & NFR Decisions
Async model, storage engines, caching, background processing; every card's BECAUSE cites an F#.
▸ Dn

## 7. Failure Handling
Behaviour under failure: retries, race elaboration, error propagation, consistency guarantees;
a short "Other risks" list for orphans only.

## 8. Extension Cost
Confirmed change axes; cost of the next addition per axis ("one class + one registry entry,
zero core edits"); flexibility deliberately NOT built and why.

## 9. Open Questions
Omit when empty (a non-empty section cannot be finalized without accepted consequences).

## Decision Index
| ID | § | Title | Chosen | Origin (blueprint-L2 / adr-new) | Status |
```

---

## Recording a decision

**Lean** — in the `## Decisions` list: a clean bullet `- <plain statement>  (Dn)` each (with an
optional `★ your call`), flat for ≤5 or grouped under `### N · theme` for 6+ (see the Decisions
section above). NO `— instead of X` tail — the rejected alternative and the why both live in the
narrative above, said once (Principles #4–5).

**Full** — an inline card where the decision turns on a weighed force:
`▸ DECISION Dn — CHOSEN: … · OVER: … · BECAUSE: <F# → consequence> · ASSUMES: X — if not, Y`.
Stable IDs. There is NO separate "Trade-offs & Alternatives" section — the OVER/BECAUSE on every
card is the record.

**Both shapes: accepted decisions FREEZE.** A conclusion change spawns a superseding decision (a
new ADR, or the same ADR's next revision, referencing `ADR-XXX·Dn`), never an in-place edit.
