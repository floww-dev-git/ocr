---
name: write-user-stories
description: "Write role-scoped user stories with Given/When/Then acceptance criteria from a FINALIZED PRD (or delta-stories for class-2 updates). The canonical story format — one home, invoked by /intake-requirement Step 9 and directly via 'format user stories from plan', 'write user stories'."
argument-hint: "[finalized PRD path, or confirmed-intent + flow docs for a class-2 update]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write
---

# Write User Stories

Write stories for: $ARGUMENTS

The single home for the user-story format. Invoked by `/intake-requirement` Step 9 (Gate 1b) and
directly when a finalized plan needs stories.

## Input Contract

Stories are DERIVED, never invented. Legitimate inputs:
- **Class 1 (new concept / extension):** the **confirmed** `flows.md` (the ✓ flows checkpoint
  passed) + the finalized PRD for vocabulary and scope. Never a draft PRD, never unconfirmed
  flows — a story must not cite a journey the user hasn't seen and blessed.
- **Class 2 (update):** the confirmed-intent line + the existing `flows.md` under
  `<app>/docs/features/<slug>/`. No new PRD is written for a class-2 update.
- **Legacy concepts with no PRD:** allowed — the Given clause records prior behavior. Never
  retro-author a PRD to satisfy the input contract.

If the input is a draft PRD, unconfirmed flows, or has unresolved Open Questions, stop and bounce
back — do not author stories on shifting ground.

## Story Format

One story per role-scoped capability:

> **As a** [role], **I want** [capability], **so that** [benefit].

Each story carries:
- **The flow step it serves** — every story cites its step in `flows.md`; a story serving no
  flow step is invented, not derived.
- **Acceptance criteria** in Given/When/Then form, written in domain vocabulary — the canonical
  terms from the PRD's terminology table (code reuses these exact terms downstream; do not invent
  synonyms).

## A Capability Assertion Is Not an Acceptance Criterion

### WHY
A config flag shipped unreachable: US-6 AC1 read "a document template CAN BE MARKED as a live
letter via the flag." That AC was satisfied by the model FIELD merely existing — the read path was
built, the write/authoring path never was, so the flag could only be set by a raw DB write, and the
story still passed as done. The UI read surface (`has_live_letter_access`) was never modeled at all:
a YAGNI trim of the set-mutation silently dropped the read surface too. The root cause was the AC
form — "can be marked" asserts a CAPABILITY, not a traced flow, so nothing forced either edge to be
built.

### The Rule — a new CONFIG FLAG or FIELD must trace end-to-end on BOTH edges
When a story introduces a config flag/field (anything an admin sets that a consumer later reads),
its ACs must trace it on both edges — a capability sentence is not enough:

- **WRITE / authoring edge** — a real admin input reaching the DB. Name the concrete mechanism:
  which CSV column / configio round-trip / GraphQL mutation sets it. "Can be marked" with no named
  write mechanism is an unbuilt path wearing a done costume.
- **READ / consumption edge** — the DB value reaching a consumer/UI. Name the query/field/resolver
  that surfaces it (`has_live_letter_access`-style read surfaces are modeled, never assumed).

Both edges get a Given/When/Then AC. A field's mere existence in the model is never the acceptance
criterion — the traced flow is.

### Inheritance default
If an existing round-trip pattern already covers sibling fields (e.g. template scalars round-trip
export⇄populate on one shared CSV column in letters configio), the new field **inherits that pattern
by default** — the AC states the inheritance ("round-trips through the same export/populate column as
its siblings") rather than re-deriving a bespoke path. Trimming the new field OUT of an established
round-trip is a scope decision the user must confirm, not a silent YAGNI.

This is the story-authoring face of the architect's **T5 parity check** (`t-triggers.md`): T5 catches
the gap at Phase-B entry against live code; this catches it at authoring time, before code exists.
- **Edge cases** — each traced to a specific flow step it stresses.
- **Permission requirements** — which role/permission the story presumes, per story.
- **Error-path stories** — derived from the PRD's Error Scenarios table (one story per meaningful
  failure, not folded into happy-path ACs).

## Class-2 Delta-Stories

For updates, each delta-story cites the flow step it modifies:

> Flow F3 step 4: X → Y.

**Canonical flow doc — `flows.md` under `<app>/docs/features/<slug>/` (single home; PRDs no
longer carry flows):**
- If it exists → patch it with the delta.
- If it doesn't (legacy concept) → **BOOTSTRAP**: the same Gate-1b pass writes a minimal
  `flows.md` recording CURRENT behavior first (the input contract's "Given clause records prior
  behavior" sanctions this), then patches it with the delta. Never skip the bootstrap and cite
  steps that exist nowhere.

`flows.md` MUST be patched in the same Gate-1b pass — no orphaned flow changes where a story
references a step the flow doc doesn't yet describe.

Class 4 (refactor) uses the same bootstrap when the behaviour under refactor has no
flows/stories — but sourced from the architect's `/design-module` Step-0 parity inventory, not
a PRD (Phase A never reads code; the inventory is the ground truth of current behaviour). See
the Class-4 check in `/intake-requirement`'s `references/triage-classes.md`.

## Provenance Discipline

Stories are the WHAT — the requirement level. Mark every statement **confirmed** (traces to an
allowed source below) vs **assumed** (a question surfaced at the gate, never a silently-authored
AC). No invention: thin input produces clarifying questions, never padded stories.

### Allowed provenance — what a story MAY cite
- **Flow steps** — `F3 step 4` (the journey the story serves; every story cites one).
- **Parity-study rows** — the behaviour catalogue's `A`/`B`/…/`F#` rows AND its `D1–D4` / `C1–C4`
  rows (class 4 / class 2 refactor input). These are CURRENT-BEHAVIOUR facts with code refs, not
  design decisions — citing them is legitimate provenance.
- **PRD terminology** — the canonical domain terms (reused verbatim downstream; no synonyms).
- **The user's own words** — a directly-quoted requirement.

### Banned provenance — what a story must NEVER cite
- **ADR numbers (`ADR-NNN`)** and **ADR decision cards** (a `Dn`/`Cn` that lives in an ADR). A
  story is a requirement; an ADR is a design record that SERVES the requirement. The link runs ONE
  way: the ADR cites the stories it serves (its header already does) — a story never points back at
  an ADR. WHY: ADR numbers move (a renumber is routine — REF-001 just did), so a story citing
  `ADR-004·D2` rots the moment the ADR is renumbered; and pinning a requirement to a design decision
  inverts the dependency (the WHAT must not depend on the HOW).
- **The subtle trap:** parity rows and ADR cards share the `D#`/`C#` notation. Tell them apart by
  the artifact they live in, not the letter — parity `D1–D4` / `C1–C4` (behaviour rows in the
  parity study) are ALLOWED; a `Dn`/`Cn` decision card that lives in an ADR is BANNED.

## Epic Organization & Save

Stories live with the app that owns the capability — ONE file per epic:
`<owning_app>/docs/user_stories/<epic-slug>.md`. They are grouped by epic, but they sit OUTSIDE
the feature folder.

WHY both halves matter:
- **Grouped by epic, not by feature.** An epic is a product capability. It outlives any single
  feature — several features add stories to the same epic over time. So a story cannot live in
  a branch-scoped feature folder; that would split one capability across many folders.
- **Inside the owning app, not at the repo root.** Every other doc lives with the app that owns
  the business logic (`dev-loop.md`: "Docs live with the owning app"). Stories are not an
  exception. A reader who opens the app to learn what it does finds its stories there.
  (Ruling 2026-07-15. This reverses the 2026-07-11 repo-root move, which was right that an epic
  outlives a feature but overshot: stories only needed to leave the FEATURE FOLDER, not the APP.)

- **Pick the epic first.** Reuse the existing `<owning_app>/docs/user_stories/<epic-slug>.md` if
  the capability already has one (APPEND the new stories); create a new file only for a genuinely
  new epic. `<epic-slug>` is kebab-case, names the capability (`execute-transition`,
  `multi-workflow`), never the feature/branch.
- **Pick the owning app the same way the feature folder does** — the app that owns the
  capability's business logic. A capability spanning several apps lives in the PRIMARY owning
  app, in one place. Do not split one epic across apps.
- **US ids are unique within the epic file.** A feature appending to an existing epic continues
  the numbering (US-11, US-12…) — never restart at US-1 and collide with an earlier feature's stories.
- **Flow citations qualify their source.** Flows stay per-feature
  (`<owning_app>/docs/features/<slug>/flows.md`). A story cites `<slug> · F3 step 4` so the
  journey stays unambiguous once an epic file spans features. For a single-feature epic the
  `<slug> ·` prefix may be omitted.
- **Single-writer discipline** (`agent-teams-pipeline.md`): the epic file is SHARED across
  branches. Re-read it fresh from disk and APPEND a targeted edit; never regenerate it from
  conversation context (that wipes another branch's stories).
- **Feature ↔ stories link:** `feature-context.md` records which epic file(s) + US-ids this
  feature serves; the ADR header cites the same `<owning_app>#<epic-slug>#US-ids`. That pointer
  is the bridge from a feature to its stories.

### Legacy location during migration

Repo-root `docs/stories/<epic-slug>.md` is the OLD home. Some epic files still sit there while
they are being moved. When looking for an existing epic, check the app path first, then fall
back to the repo root. Write NEW stories only to the app path. Do not move old files as a side
job — the migration is its own approved task.

Present for **Gate 1b** approval. Gate 1b is the Phase-A exit.
