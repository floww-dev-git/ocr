---
name: module-blueprint
description: Produce a Module Blueprint — an interactive, logic-first HTML design report that walks a design outside-in: the model (logical layers + entities, one picture) -> the exposed interface (public API) -> the behaviours behind it. Use when the user says "module blueprint", "design walkthrough", "interactive design doc", "design report", or when the architect wants to de-risk an ADR by confirming the domain model pass-by-pass before writing it.
argument-hint: "[feature or subject to blueprint, e.g. 'workflow_engine feature 1']"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Module Blueprint

Produce an interactive Module Blueprint for: $ARGUMENTS

A Module Blueprint is an **optional Phase-1 enrichment** the architect produces after user stories and before the ADR. It de-risks the ADR by getting the domain model confirmed pass-by-pass. It is NOT a new approval gate — it feeds the ADR.

The blueprint is Phase B's IDEATION beat. It is the divergent exploration surface: entity taxonomy, layer cuts, and alternatives are tried and weighed on decision cards before anything hardens. The "model locked ✓" converges that exploration. The ADR merely records what the exploration decided.

The **canonical exemplar** is `workflow_engine/docs/design/workflow-engine-design-walkthrough.html` — match its shape. This skill was last aligned to the exemplar at commit `f0d64ec14f` (2026-07-02); if the exemplar has moved since, re-read it before trusting the structural notes below.

### Reference examples — study these before authoring a Pass-1 walkthrough

Two shipped, worked walkthroughs on disk. Read the one that matches your module's shape and mirror it:

- `boards_engine/docs/design/boards-engine-design-walkthrough.html` — the **visual-toolkit + outside-in content-architecture** reference: the module → the door → the behaviours, with sub-module division panes. Study this for the standard structure of a Pass-1 walkthrough.
- `bps/docs/features/pmu-relieve-officer-dev403/design/relieve-officer-design-walkthrough.html` — the **sub-module FLOW-graph** reference: how to draw a workflow/orchestration module as an ordered flow, not a dependency web. A top-to-bottom flow canvas (sync lane: initiate → guards → start-background-job) hands off to an async execution-backbone block drawn as a bordered container wrapping a VERTICAL ordered step stack (deactivate → reassignment → batch → finalize) with a failure path and COMPLETED/FAILED result terminals; read-only side nodes (suggest, retry) sit on dashed edges; canvas cards stay lean (title + badge + deep-dive chip) with all descriptive detail in the side deep-dive panes.

## The model is derived inside-out, but READ outside-in

You do the thinking inside-out (nouns → verbs → home each verb → the layers emerge). The reader consumes it outside-in, in **three passes**:

```
Pass 1  The model            logical layers + entities · one picture
Pass 2  The exposed interface the module's public API · one door per use case
Pass 3  Behaviours           the verbs behind the door · grouped by layer
```

Two rules govern the whole artifact:

- **Logical layers, not folders.** The model names concerns and separations ("who does what") — never packages. A package name appears only as a collapsed "projected package" row inside a layer's side pane, decided at ADR/plan time. See @.claude/skills/module-blueprint/references/layer-boundary-heuristics.md.
- **Ruthless progressive disclosure.** ONE picture on the page; every contract, port catalog, and meta detail lives behind a click (side pane) or a hover (popover). Delete any narration of what the diagram already shows — a "separations" table next to a diagram that already draws the separations is noise.

The visual toolkit (stepper · layer-stack diagram with embedded entity chips · clickable layer boxes → side panes · `<details>` behaviour rows · dotted popovers · composite edge band · source-citation footer) lives in the template. **Fill the template — do not hand-derive CSS, JS, or the palette.**

## Process — logic-first & incremental (do NOT one-shot the HTML)

### 1. Verify names against real source FIRST
Before writing a word, confirm every entity, field, enum, and method name against the actual source files (`Read`/`Grep`/`Glob`). This module has been bitten by hallucinated entity names — see architect memory. Proposed method/type names that don't exist yet are fine ONLY if the footer labels them as proposed. Keep a running list of the exact files you verified — the footer must cite them.

### 2. Derive the model (confirm each step as plain text before the next)
Follow @.claude/rules/agent-interaction.md ("Building Deliverables" — logic-first, incremental) and, for the exploration itself, `superpowers:brainstorming`. Surface each step as a lightweight text skeleton for a quick alignment check — do not disappear and return with a fully-formatted artifact.

- **a. Entities & scope.** Draft the noun list and the owns/references split. **Confirm before moving on.** A wrong noun set poisons every later step.
- **b. Behaviours & homing.** For each entity, list its verbs and **home each one** using the behaviour-homing test: *name the scope in the question — that's the host entity.* A batch/plural question ("which transitions can this item take from this stage?") lives on the scope entity (Stage), not the subject (Transition). Apply the **signature litmus**: every behaviour is either *definition-time* (about the shape — no item in the signature, cacheable) or *item-time* (a decision about one item — item always present, usually via a `context`). A signature that fits neither is two behaviours conflated. A redundant param is allowed only as an explicit staleness assertion. Confirm the homing.
- **c. Classify the taxonomy — entities ≠ layers.** They are two different taxonomies. Sort every entity into exactly one bucket, and never label an entity with its layer's name:
  - **The subject** — the one entity every layer answers a question *about* (e.g. Transition). Belongs to NO layer.
  - **Core entities** — read-only foreign nouns the module references but never manages (e.g. Workflow, Stage). Read *through* the Fact-providers layer; they are NOT "fact providers".
  - **Engine-anchored entities** — the entity an engine runs (e.g. Guard → Guard engine, Transition logic → Transition logic engine). Only these live inside a layer.
  - **No-entity layers** — pure behaviour, own no entity (e.g. Orchestration, Authorization).
  Confirm the buckets.
- **d. Name the logical layers (naming gate).** Name each layer/component and run the gate:
  - **Entity-anchored & self-explanatory.** If a name needs a popover or legend to be understood, it is wrong. Name an engine after the entity it runs ("Guard engine", not "decision core").
  - **No architecture-speak, no synonyms.** One word per concept — don't invent a synonym for an entity that already has a name ("gate" for an existing "guard" is killed).
  - **Domain-vocabulary collision check.** Check the proposed name against reserved domain terms before using it (in this project "authority" = a sanctioning body like GHMC/DTCP, so an RBAC layer is "Authorization", not "authority"). See architect memory for the locked vocabulary.
  Record the projected package for each layer as a deferred note only. Confirm the layer set.

### 3. Fill the template — outside-in
Copy `references/module-blueprint-template.html` and fill only the marked zones, in the reader's order:

- **Pass 1 · The model.** One layer-stack diagram: the subject on top, layers stacked below in call order, the **composite edge band** at the bottom (Fact providers + the external world as one box with an internal dashed divider labelled "reads, never writes — the app boundary"). Embed each entity as a `.echip` inside its layer box (core entities inside the edge band). Every `.lbox` with a layer and every `.echip` is clickable → a side pane. NO meta table or callout on the page — the "question it answers · nature · hard boundaries · projected package" all live in the layer's pane. **For an engine/mechanism module, the Fact-providers layer DEFINES the ports** (interfaces only) and the **producer apps implement them**, injected at the resolver — the engine imports zero other apps; the edge-band and its pane say exactly that, and the projected package is `ports/`, not `gateways/` (run the dependency-direction check in `references/layer-boundary-heuristics.md`).
- **Pass 2 · The exposed interface.** PUBLIC API ONLY — one row per exposed method, traced to the composed behaviour behind it. Consumed ports are **NOT** exposed. They live in the Fact-providers layer pane as a port catalog, each traced to the behaviour that needs it and to its producer app. **The interactor mirror lives here**, not in an engine deep dive. Render it as a collapsed `<details>` titled "The composition behind the door — `<Interactor>`", placed directly under the exposed-API table. Inside, show the use-case main method as annotated code — each step is a chip coloured for the layer it calls. The code IS the Pass-1 diagram read top-to-bottom. It sits in Pass 2 because it is **orchestration** content — the composition behind the exposed door — not any single engine's internals.
- **Pass 3 · Behaviours.** The internal verb catalog: one `.eg2` group per layer-group (core entities · the subject · each engine), one `<details>` per entity, one `.verb` row per behaviour tagged by responsibility cluster. Carry the signature-litmus takeaway.
- `POPS` entry per jargon term; `PANE` entry per clickable box/chip (layer panes include a "Projected package" row; entity panes include a "Logical layer" row).
- Footer cites the real source files verified in step 1 and marks proposed names as proposed.
- **Do not touch** the CSS or the popover/side-pane JS engines. Theme = one `:root` swap (light GitHub default; Catppuccin dark variant is a commented block).

### 3b. L2 — the engine deep dive (optional, per decision-heavy engine)

L2 is a **zoom level, not a scroll**: L0 is this one-picture model page, L1 is the side panes (a layer's or entity's contract), L2 is a **full-screen in-page deep dive of ONE engine's internals**, opened from a "Deep dive — engine internals →" button in that engine's layer pane. A tinted band + breadcrumb marks it; Esc or the breadcrumb returns to L0. The reader contract: **no level requires the one below it** — the model reads complete without any deep dive.

**When to add one — the decision-density gate (EARN IT).** Design effort ∝ decision density, not surface area (architect framework #9). A deep dive is earned ONLY by a decision-heavy submodule — an OCP surface or engine with real open design questions. CRUD, pass-through reads, and no-entity plumbing layers (Orchestration, Fact providers) **never** get one. The hard rule: **no decision cards → no deep dive.** If you can't fill even one decision card, the layer's L1 pane is the whole story — delete the placeholder `ddview` section.

**The drill-down mechanic is already wired in the template.** Copy the placeholder deep-dive section once per qualifying engine. The wiring steps — the PANE field that opens it, band tinting, and per-engine id prefixing so multiple deep dives don't collide — are documented in the template's own comments (search `ddview`); the open/close/Esc JS engine is done, do not touch it.

**A deep dive is TABBED — every tab is a READER QUESTION, and every tab is about THAT engine** (`.ddtabs`/`.ddtab`/`.ddpanel`). Label the pills as the questions a reader arrives with, not as internal artifact names. The standard three, kept only where the engine answers them:

- **How it works** (always) — the run, as a phased narrative (see content grammar).
- **Add a &lt;plugin&gt;** (only for OCP surfaces) — the extension recipe + receipt.
- **Why this design** (always — this is why the engine earned a deep dive) — the decision cards.

**Coherence rule — every tab stays inside this engine's boundary.** A tab that describes something *above* the engine (how a use case composes several layers) is orchestration content and does NOT belong in an engine's internals. The classic violation is a "The interactor" tab: the interactor mirror is orchestration — it lives in **Pass 2** as the "The composition behind the door — `<Interactor>`" disclosure, not here. A bad tab *name* is the visible symptom; the disease it flags is a **taxonomy violation** — content sitting in the wrong scope. The naming bar is how you catch the structural bug: if you can't name a tab as a question *about this one engine*, the content is misplaced.

**The content grammar.** No sequence diagrams: implementers think in classes, not swimlanes.

- **"How it works" is a PHASED NARRATIVE, not a card gallery.** Open with one line naming the phases (e.g. "declare → wire → execute"). Then take each phase in turn: a "Phase N · Title — subtitle" heading, followed by a 2-4 sentence **prose paragraph that carries the causality** ("to exist, it registers…; from that moment it is picked up automatically…"). **Prose comes first. Classes and tables are in-story exhibits** — they appear only where the story needs them. Use a contract skeleton, a comparison **table** of all shipping variants that fit one contract, and condensed class cards for the runtime collaborators. Each phase closes complete. The declare phase ends with a takeaway line — "That completes the &lt;plugin&gt; aspect. Everything below is machinery that runs them." The class exhibits still obey the flow grammar (arrows carry the run order) and the one-line-purpose linter (*if a purpose needs two lines, it's two classes*). But the tab's spine is the narrative, not a grid of cards.
- **The extension recipe + receipt** — a numbered `.steps`/`.stp` walkthrough, a short code skeleton, and the **extension receipt** (`.receipt` with three `.rcol` columns: ✚ create / ✎ extend-only-if / 🔒 never-touch). The receipt turns the OCP claim into an **invoice** — it prices the extension. If the 🔒 never-touch column **shrinks** in a future change, the design regressed; that shrink is the signal to catch in review.
- **Decision cards** — one `.dcard` per open design question: **question · ✓ chosen answer · why + consequence.** These are mini-ADRs — they are what feeds `/create-adr`, which transcribes them into the ADR's Decisions list VERBATIM. So write each card's TEXT in plain language and record its rejected alternative, per create-adr's plain-language rules + banned-words list (`.claude/skills/create-adr/SKILL.md`): describe what the thing does, never a pattern's name ("plug in a new picker", not "the strategy pattern"). The blueprint's own HTML surface may keep its working vocabulary (popovers define terms), but the card text a reader carries into the ADR must stand plainly on its own. Order cards by weight, decision that most shaped the design first. For a centralized extension surface, include the two invariants the exemplar carries: *plug-ins hold gating policy, never domain math* (compute a foreign value → new port, not a fatter plug-in), and *who implements the ports* (producers, so the engine imports zero apps) — see `references/layer-boundary-heuristics.md`.

### 4. Save and open
- Save under the owning app: `<owning_app>/docs/design/<slug>-design-walkthrough.html` (the app that owns the domain logic owns the doc — see @.claude/rules/dev-loop.md).
- **Cross-link the living review page** — the blueprint header carries a link to the feature's living review page (`review-<slug>.html` at the worktree root), and the living page gains a link back to the blueprint. Link, never inline — the blueprint stays its own surface (single-writer).
- Open in the browser: `open "<path>"`.

## Rules

- **Verify before writing** (@.claude/rules/investigate-before-answering.md) — no entity, field, or enum name goes in the blueprint unread. The footer's citation is the proof.
- **Layers before folders** — the page names concerns; packages are a deferred, collapsed note inside a pane.
- **One picture, everything else behind click** — no table or callout duplicates what the diagram shows.
- **L2 is earned, not default** — a deep dive exists only for a decision-heavy engine with real decision cards. No decision cards → no deep dive. Zoom levels, not scroll: no level requires the one below it.
- **One-line purpose is a linter** — in a deep-dive class map, a purpose that needs two lines means two classes. Split it.
- **Derive, don't invent** — the exposed interface traces to behaviours, which are homed on entities, which are classified into the layer model. If a layer has no behaviour behind it, or an interface no behaviour, cut it.
- **Confirm each step** — this is the point of the artifact. Do not batch the derivation into one silent render.
- **Design only — no code.** The blueprint proposes the model; `/create-adr` records the decision and `/task-breakdown` commits to names.
- **Fill, don't rebuild** — the palette, stepper, diagram, panes, popovers, and legend are done. Your job is the domain content.
