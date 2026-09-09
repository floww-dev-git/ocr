---
name: create-adr
description: Generate or rewrite a feature-scoped design record (ADR) — written in plain language and flexed to the size of the change: a lean What / Behaviour / How-it-works / Decisions shape for a small or medium change on an established pattern (the default), a fuller shape only for a large or novel design. Records every decision with the alternative it was chosen over. Use when the user says "create ADR", "write an ADR", "rewrite ADR", "trim ADR", "update ADR", "document architecture decision", or needs to formally record or significantly revise a design decision.
argument-hint: "[feature or use case description]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write
---

# Generate ADR

Create or rewrite an ADR for: $ARGUMENTS

## Scope

This skill applies to:
- **New ADRs** — creating from scratch based on user stories or a feature description
- **Significant rewrites** — trimming, restructuring, or applying multiple corrections to an existing ADR

If `$ARGUMENTS` is a file path to an existing ADR, read it first and use it as the starting point. Preserve decisions and rationale that are still valid; only restructure, trim, or correct as requested.

## Process

1. **Read the inputs** — dispatch manifest → the PRD's four sole-witness sections (Out-of-Scope, Constraints & Dependencies, Domain Terminology, Error Scenarios) → `flows.md` → stories → **the Module Blueprint when one exists (mandatory read — transcribe its L2 decisions into this ADR's decision list, marking origin `blueprint-L2`; never re-derive them)** → the locked schema from `/design-db`. If rewriting, read the current ADR first.
2. **Clarify** — answer first from those inputs; ask the user only what they leave open (asking what the pipeline already learned is a clarity-cascade failure). Cover: failure modes, concurrency, migration strategy, anticipated change axes (confirmed vs speculative), rejected alternatives.
3. **Pick the shape by change size (default lean).** Two shapes live in `references/adr-template.md`:
   - **Lean (the default)** — a small or medium change on a pattern the codebase already has (a new type plugged into an existing registry, a new field, a new node on an existing engine). Sections: `Problem` (what's broken, 2-4 plain lines) → `What we add` → `Behaviour` → `How it works` (a diagram) → `Notes` → `NFR notes` (opt-in — only when the change has real non-functional concerns) → `Decisions`. Every ADR opens with `Problem` before any solution; drop any OTHER section it doesn't need — `NFR notes` included: a small change on an established pattern usually has none.
   - **Full** — a large or novel design (a new engine, a new app, a cross-app boundary being invented, real NFR forces to weigh). Adds the fuller sections: Forces table, Design Overview, Modules & Ownership, Entities & Data, committed Interactor Architecture, Infrastructure, Failure Handling, Extension Cost.
   When unsure, start lean and add a section only when the change actually needs it. A small change wearing the full template is the drift this skill exists to prevent.
4. **Design & decide — the thinking step.** For every decision NOT carried from the blueprint (that's ALL of them when no blueprint exists — this step is then the feature's ideation beat; never skip straight to writing):
   - **Generate real options** — 2–3 per decision. Codebase precedent first ("the codebase already has three patterns for this — why a fourth?"); design patterns (registry, strategy, adapter, event-driven) are thinking tools only — they guide the weighing, they never appear as names in the ADR's text (say "plug in a new picker", not "the strategy pattern").
   - **Weigh by simplicity, then by the forces that apply** — the simplest option that meets the real constraints wins. Full shape: weigh against the Forces table (the option that best answers the cited F#s wins). Lean shape: the constraints are few and you weigh them in plain prose — no formal table.
   - **Run the change-axis analysis** (architect Phase 1c): list what's likely to change near-term → **ASK the user which axes they actually expect** → design extension points ONLY along confirmed axes; everything unconfirmed stays simple (easy-to-change beats built-to-extend). Full shape proves the cost in Extension Cost; lean shape states it in one plain line under Notes if it matters.
   - **Discuss the forks that matter** — scope, user-visible behaviour, and business-consequence trade-offs go to the user (`AskUserQuestion`, recommendation first). Technical shape you resolve yourself and record in the Decisions list, with an override invitation.
5. **Write per the chosen shape.** Open with the `Problem` — what's broken today, in plain words, before any solution. Then describe the design in plain words, lead each flow with a diagram (show, then tell), then record the choices in the `Decisions` list as CLEAN bullets — one plain statement + a trailing `(Dn)` id + any `★ your call` marker, grouped by theme for 6+ decisions. NO `— instead of X` tail on the bullet: the rejected alternative AND the reasoning both live ONCE in the narrative above (Problem / Behaviour / How it works / Notes), per Principles #4–5. The list is a scannable index of choices, not the argument. Blueprint-carried decisions are transcribed; new ones are authored from step 4. (Full shape only: a decision that turns on a weighed force carries its `OVER / BECAUSE` inline in its narrative section — see the template's card grammar; the Decision Index table stays clean.)
6. **Pre-handoff self-check (the architect runs this BEFORE the manager sees the ADR).** Every ADR that got hand-fixed at a gate had failed at least one of these — the gap is application, not knowledge. Run all four:
   - **Size/shape** — is it the LEAN shape? A small/medium change on an established pattern must read in ~one screen. Full shape ONLY for a novel or large design (new engine/app, invented cross-app boundary, real NFR forces). Reaching for the full shape on a settled-pattern slice is the #1 recurring miss.
   - **Problem-first** — does it OPEN with `## Problem` (what's broken), before any solution?
   - **No rule-restatement** — did you audit each decision against the rulebook (Principle #6) and cut the standing-rule restatements?
   - **Plain, grouped decisions** — jargon-free headlines; clean bullets (one statement + a trailing `(Dn)` + optional `★ your call`, NO `— instead of X` tail — the alternative lives in the narrative); 6+ decisions grouped by `### theme`; plain-language + banned-words check passed.
   - **NFR notes are non-functional only** — for EACH NFR bullet, ask: could a user story assert this with a Given/When/Then (a foreign-account read returns empty · a port fails closed on ownership · no existence leak)? If yes it is a FUNCTIONAL or security behaviour — the WHAT — and it belongs in a user STORY as an acceptance criterion, which the MANAGER owns. Flag it back to the manager for the stories; NEVER keep it in NFR notes. NFR notes hold only "how WELL" concerns — performance, caching, concurrency, resource use, availability, observability — never "what the system does". (Principle #1 WHAT-vs-WHY + the manager/architect ownership boundary; REF-001 S1 wrote scoping/ownership/failure-mode behaviours into NFR notes — they moved to US-9.)
   - **Engine domain-purity scan (engine/mechanism designs only)** — if the ADR designs an engine/mechanism app (mode-2: defines ports/registries others plug into), grep the proposed engine core (table / enum-value / class / base-contract names) for producer-domain vocabulary. Each hit — a domain-named class (`ShortfallLimitGuard`), a domain enum value (`transition_type = SHORTFALL`), a fact port that exists only to pull one producer's data — is a leak and a plug-in candidate: name the producer app it plugs into before the ADR hardens. This is the cheapest catch in the pipeline (S1/S2, before code exists), not S6 after six ADRs (REF-001). Non-engine ADRs skip this and say so in one line.
   The manager gates the SHAPE before relaying, but the architect owns the ADR being BORN right — do not hand up an ADR that fails this checklist.
7. **Save** as `<owning_app>/docs/features/<feature-slug>/adrs/ADR-NNN-[short-name].md` (numbered per feature from 001; layout per `.claude/rules/references/feature-folder.md`; standalone one-off ADRs with no feature go to `<app>/docs/adrs/`), then declare the scope fence. If an implementation plan already exists for this ADR (rewrites), keep a single `**Implementation plan:** [path]` pointer line in the header block — path only, never task content. For new ADRs, `/task-breakdown` adds this line when it generates the tasks file. **Declare the scope fence** — the header carries ONE clear line, `**Declared modules:**` followed by the touched dirs as backticked, comma-separated real dir paths (e.g. `dir/one`, `dir/two`). Keep the exact `**Declared modules:**` token (not a vague `Scope:`) on its own header line directly under Status — it's the greppable fence the reviewer and `/self-review-checklist` check the diff against, and it reads plainly enough to double as the human scope line. The ADR is where module knowledge first exists with code evidence, so the ADR header is where the fence lives. Growth is a scope change: only the architect widens the line, via an ADR rewrite + user approval through the Design Correction Protocol; the developer NEVER edits it. Rewrites re-emit the line — overwrite, never accumulate.
8. **Present the Gate-2 digest — never the raw document** (see Gate-2 Digest section).

## The Template

Fill `references/adr-template.md` — don't hand-derive the structure. It holds BOTH shapes:

- **Lean (default):** header (Status line, then the `**Declared modules:**` fence on its OWN line,
  then optional Blueprint/plan/Stories pointers) → `## Problem` (what's broken, before any solution)
  → `## What we add` → `## Behaviour` → `## How it works` (diagram first) → `## Notes` (only what's
  needed) → `## NFR notes` (OPT-IN — clean grouped bullets by disposition: Designed (must-have) /
  Deferred (with reason) / Non-issues (with reason); omit the whole section when the change has
  none) → `## Decisions` (the 30-second scan; group by theme for 6+ decisions).
- **Full:** the same header → §1 Context + Forces table → §2 Design Overview → §3 Modules & Ownership
  → §4 Entities & Data → §5 Interactor Architecture (committed) → §6 Infrastructure & NFR → §7 Failure
  Handling → §8 Extension Cost → §9 Open Questions (omit when empty) → Decision Index.

The Decisions list / Decision Index and the freeze/supersede rules live with the template.

## Plain-language rules (both shapes)

The reader is a non-native English speaker. Short sentences, one idea per line. Describe things by
what they DO, not by implementation jargon.

**Banned words — the shared list:** `.claude/rules/references/plain-language.md` (say each one
plainly). If a sentence needs a fancy word to sound right, rewrite the sentence.

## Principles (a document violating these fails review)

1. **WHAT-vs-WHY** — what to build → `/task-breakdown`; why it's shaped this way → here.
2. **Name-replacement test** — if a specific name (enum, method, class) can be replaced by a description of what it does and the point still holds, it belongs in the breakdown. Exception: use-case DOOR names — naming the use case IS the boundary decision. Brief illustrative examples may follow.
   - "Add `PIPELINE_STAGE` to `RuleEntityType`" → breakdown. Here: "Extend the rules engine entity types to cover pipeline stages".
   - "New `PMU_ACTION_CONTROL` purpose enum" → breakdown. Here: "A new rule purpose governs which PMU actions are permitted per stage".
   - "`get_entity_rule_sets(entity_type=…, purpose=…)`" → breakdown. Here: "The rules engine already supports entity-scoped, purpose-keyed queries".
3. **Pattern names never decorate the text** — registry / strategy / adapter are thinking tools during step 4; the ADR says what the thing does ("plug in a new picker"), never the pattern's name.
4. **Every decision's rejected alternative stays on the record — in the NARRATIVE, not on the bullet.** The whole point of the record is what was chosen AND what it beat, for a future reader — so the alternative belongs in the `Problem` / `Behaviour` / `How it works` / `Notes` prose, where the reasoning already lives (Principle #5), said once. The `## Decisions` list stays a clean scannable index: one plain statement + `(Dn)` + optional `★ your call` — never a `— instead of X` tail. A genuine fork whose narrative names no alternative is still incomplete. (Full shape: the `OVER / BECAUSE` card is itself inline in its narrative section — same rule; the Decision Index table stays clean. A card citing no force is unjustified; a force no card answers is an attention flag at the digest.)
5. **Say the why once** — the reasoning AND the alternative it beat live in the narrative above the Decisions list; the list records the CHOICE only and never repeats the argument.
6. **Don't restate conventions** — standing project rules earn no ink; only deviations do. Before saving, AUDIT every decision against the rulebook and CUT any line a reader would already get from the rules alone. Usual suspects that keep sneaking in dressed as "decisions" (they are NOT — they are standing rules): rich domain objects inside `workflow_engine/` (`rich-domain-models.md`), no cross-app foreign keys / DTO-only boundaries (`clean-architecture.md`, `models.md`), the engine-defines-ports direction (`clean-architecture.md`), guards/interfaces grown from consumer demand (`interactors.md`, `storages.md`). If a decision only says "we followed rule X", delete it.
7. **Assumptions ride their decision** ("ASSUMES: X — if not, Y") — never a separate section.
8. **Accepted decisions freeze** — supersede, never edit (a whole-doc Status covers the document; per-decision status covers partial supersession).
9. **Plain language** — obey the banned-words list above; if a phrase needs explanation, rewrite it ("per-stage PMU action control" → "which PMU actions are allowed at which stage").

## Gate-2 Digest (what the user reviews — one screen)

Present this, not the raw ADR. The full document is linked for spot-checks — a prerogative, not an obligation.

1. **Header strip** — fence dirs · blueprint status ("N L2 decisions carried ✓ · M new at ADR time") · stories served. Carried decisions were already approved at the blueprint pass, so the digest SPOTLIGHTS the new ones.
2. **Decisions** — the Decisions list rendered (lean: clean bullets `<statement> (Dn)`, grouped by theme — the rejected alternatives are in the narrative, not here; full: the `Dn · CHOSEN · OVER · BECAUSE` cards), new-at-ADR first. These also land on the decision log — the `#/decisions` sub-page of the living review page.
3. **NFR constraints (full shape only)** — the Forces table + the F# → Dn answer map; an unanswered force is itself a flag. Lean ADRs skip this — they had no formal forces table.
4. **Extension cost** — one line per confirmed axis (or "none" for a lean change on an existing pattern).
5. **⚠ Attention flags** — risky ASSUMES (a material "if not, Y") · open questions · convention deviations · a fence wider than the dispatch manifest's candidates.

Approve via `AskUserQuestion`. The digest renders as the living review page's `#/design`
sub-page (see `intake-requirement/references/review-page.md`) — markdown for truth, HTML for
comprehension.
