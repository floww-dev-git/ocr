---
name: design-module
description: The architect's Phase-B driver — takes a dispatched feature from entry read to approved plan through one of two lanes: a feature lane (class 1 small / class 2: entry → [blueprint?] → model ✓ → DB design → ADR → plan) and a module lane (class 4 / module-scale class 1: parity inventory → slices → per-slice design loop). Use when the user says "design module", "design a module", "module design", "consolidate X into a module/engine", "design an engine", "plan the design phase", "design lane", or an approved scope covers module-scale work.
argument-hint: "[module subject, e.g. 'workflow engine consolidation']"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Bash, Skill, AskUserQuestion
---

# Design Module

Module-scale design for: $ARGUMENTS

A module is not a feature. A feature arrives as user stories and slots into an existing shape; a module REPLACES or CREATES a shape — usually consolidating behavior that already exists, scattered. Designing it like a feature fails in a specific way: the requirement doc describes the intended module, not the live system, and the design silently drops behaviors the doc never mentioned. (Origin: REF-001 — the requirement covered ~60% of what was implemented and missed 14 behaviors; the gap surfaced only because a parity study was improvised.)

This skill sequences the architect's existing tools — it owns the *order and the gates*, not the artifact formats. Blueprint format → `/module-blueprint`. ADR format → `/create-adr`. Task format → `/task-breakdown`. Load `.claude/rules/references/engineering-canon.md` before Step 0 — the slicing, ordering, and contract rules below are its process form.

## Lane selection (mechanical — no judgment)

The lane comes off the dispatch manifest's class — the confirmed class picks the lane, never judgment.

- **Class 4 (refactor) or module-scale class 1** → **module lane** (Step 0 onward, as-is below).
- **Class 1 (feature-scale) / class 2 (update)** → **feature lane** — keep it CHEAP; class 2 pays no parity or slicing ceremony:
  - **f1. Phase-B entry** per `.claude/rules/references/phase-b-entry.md`, including the T1–T6 ledger + grounding ✓.
  - **f2. Optional `/module-blueprint`** — the ideation/exploration beat, storage-agnostic, earned by decision density; skipped for small or well-understood changes.
  - **f3. "model locked ✓"** — when a blueprint exists, no schema and no ADR authoring until its passes are confirmed.
  - **f4. `/design-db`** — schema as a projection of the locked entities (never before the lock: tables designed first anchor the entities to storage shapes).
  - **f5. `/create-adr`** — class 2 is usually an AMENDMENT to the feature's existing ADR (pass its path as the argument).
  - **f6. `/task-breakdown`.**

## Step 0 — Behavior-Parity Inventory (before ANY design)

(module lane; Step 0 doubles as the Phase-B entry read — fill the T1–T6 ledger from the inventory and deliver the grounding ✓ digest before Step 1)

The requirement doc is a hypothesis about the system; the code is the fact. Audit before designing:

1. **Inventory what the code actually does today.** Read the live implementations the module will absorb — executors, config blobs, advisory overlays, handlers. Grep for callers and side effects. This is an *audit*, not a context-building read (understanding is the entry read's job; this builds a coverage ledger).
2. **Build the parity table** — one row per current behavior: `behavior → source file → requirement-doc coverage (covered / missing) → verdict (keep / change / drop)`. When boarding as a class-4 refactor (dispatched straight from triage), also draw the **before→after module graph**: modules {new · updated · absorbed/retired} with their edges — the parity table says what survives, the graph says where it lives. This step IS the class-4 Phase-B entry depth (pair it with the T1–T6 ledger per `.claude/rules/references/t-triggers.md`).
3. **Flag the debt found on the way** — illegal cross-app imports, schemaless config, duplicated logic — classified per Phase 1b (blocking / adjacent / deferred).
4. **Save the study** under the owning app: `<owning_app>/docs/<slug>-study.md` (or `.html` for a large one).
5. **Gate: confirm the verdicts.** Every `change` and `drop` row is a user decision (visible behavior is changing); `keep` rows are announce-and-execute. Present via `AskUserQuestion` where enumerable.

## Step 1 — Slice by User Flow

Carve the module into features **by user flow** (what a user does end-to-end), not by architecture layer. For refactor boarding (class 4), slices seed from the parity inventory's behaviour groups. If the dispatch manifest says **bootstrap required** (no canonical flows/stories existed at intake), hand the Step-0 inventory back to the manager BEFORE slicing — flows ✓ then stories ◆1b derive from it (user ruling 2026-07-04, REF-001) — and slices then trace to those stories like any other lane. Propose the slice list with a one-line scope per slice and a recommended order (foundation flows first, parity-critical flows early). **Gate: confirm slices and order.**

Design proceeds ONE slice at a time. No code for a slice until its design is locked.

## Step 2 — Per Slice: Blueprint → model ✓ → DB → ADR → Plan

For each slice, in order:

1. **Domain model** — `/module-blueprint [slice]`. Entities → behaviours → logical layers → exposed interface, confirmed pass-by-pass. Decision-heavy engines earn L2 deep dives with decision cards; run the dependency-direction check (engine-defines-ports vs consumer-adapters) before projecting packages — and for an engine/mechanism, run the domain-purity scan: grep the proposed engine core for producer-domain names; each hit is a plug-in candidate, not an engine class (`clean-architecture.md` mode 2; create-adr §6).
2. **Model locked ✓ → DB design** — once the blueprint's passes are confirmed ("model locked ✓"), run `/design-db` where the slice adds or changes entities — schema as a projection of the locked entities, never before the lock.
3. **ADR** — `/create-adr [slice]`. The blueprint's decision cards ARE the decision section; transcribe, don't re-derive. The blueprint's decision cards land in the ADR as ▸ DECISION cards (origin: blueprint-L2) and later surface in the tasks file's `## Decisions` footer and the feature's decision log — transcribe, don't re-derive. Include the Extension Cost section (the change axes confirmed in Phase 1c).
4. **Plan** — `/task-breakdown [ADR path]`. Deep tasks only for the decision-heavy engines; everything else is task-lines (architect framework #9).
5. **Gate: slice design locked** → hand to the orchestrator for the dev loop. Then next slice.

## Rules

- **Audit before design** — Step 0 is not skippable when the module absorbs existing behavior. For a green-field module with nothing to absorb, Step 0 reduces to the debt scan of the surrounding integration points.
- **Parity rows are sacred** — a `keep` behavior that the new design cannot express is a design defect, not a scope cut. Surface it, don't drop it.
- **Parity preserves BEHAVIOUR, not SCHEMA** — when the module extracts legacy code into a NEW abstraction, a parity row is a behaviour to keep, never a schema shape to mirror. Do NOT copy an overloaded legacy enum or column into the new core "for migration fidelity" — decompose it along the new abstraction's OWN generic axis plus data. Fidelity is proven by the behaviour surviving, not by the column looking the same. (REF-001: legacy `transition_type` overloaded destination-kind WITH domain flags `SHORTFALL`/`TDR_SALE`; the fix kept destination-kind generic and re-expressed the domain flags as opt-in `guards`/`effects` data — every behaviour survived, zero domain names entered the new enum.)
- **Decision triage applies** (architect's Reply & Interaction Formats): the user decides scope, user-visible behavior changes, and business-consequence trade-offs; the architect self-answers technical shape and records it as decision cards with an override invitation.
- **One slice in flight** — do not open slice N+1's design while slice N is unlocked.
- **Lane off the manifest, never judgment** — the confirmed class picks the lane; re-classing mid-phase goes through the Design Correction Protocol, not a lane switch.
- **No code in this skill** — design artifacts only; the dev loop owns implementation.
