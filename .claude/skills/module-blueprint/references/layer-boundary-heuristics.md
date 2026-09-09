# Layer Boundary Heuristics

On-demand reference for the **model pass of the Module Blueprint** — carving a module into
**logical layers** (concerns / separations) and homing its entities and behaviours. Loaded when
the architect derives the model; not always-on.

## Layers, not folders

The output of this pass is a set of **logical layers** — "who does what" — named in domain terms.
It is NOT a package layout. A layer *projects* to a package (`authorization/`, `guards/`,
`gateways/`…), but that projection is a **deferred, collapsed note** recorded inside the layer's
side pane and decided at ADR / plan time. Naming folders now front-runs a decision the ADR owns
and invites bikeshedding over filing cabinets instead of concerns.

A "layer" here is a separation *inside* the one module — **not** a separate Django app.
App-splitting is an ADR decision, out of scope for this pass.

## Two taxonomies — entities are not layers

Entities answer "what are we talking about"; layers answer "who does what". Never label an entity
with its layer's name. Sort every entity into exactly one bucket:

| Bucket | What it is | Lives in a layer? |
|---|---|---|
| **The subject** | the one entity every layer answers a question *about* (e.g. Transition) | No — belongs to no layer; use cases compose its behaviours |
| **Core entity** | a read-only foreign noun the module references but never manages (e.g. Workflow, Stage) | No — read *through* the Fact-providers layer; it is NOT a "fact provider" |
| **Engine-anchored entity** | the entity an engine runs (Guard → Guard engine; Transition logic → Transition logic engine) | Yes — this is the only kind that lives inside a layer |
| **No-entity layer** | pure behaviour, owns no entity (Orchestration, Authorization) | The layer exists with no entity chip |

## The naming gate — run before a layer or component name is fixed

1. **Entity-anchored & self-explanatory.** If a name needs a popover or legend to be understood,
   it is wrong. Name an engine after the entity it runs — "Guard engine", not "decision core".
   No architecture-speak.
2. **No synonyms for an existing entity.** One word per concept. Don't coin "gate" when "guard"
   already names the thing.
3. **Domain-vocabulary collision check.** Check the proposed name against reserved domain terms
   first. In this project "authority" is a sanctioning body (GHMC, DTCP) — so an RBAC layer is
   **Authorization**, not "authority". See architect memory for the locked vocabulary.

## The 4 signals — a separate layer is justified when one fires

| Signal | Fires when | Exemplar layer → projected package |
|---|---|---|
| **OCP surface** | A set of variants sits behind one contract, and you add a variant *without touching the core* → registry + contract + concrete plug-ins. Usually the boundary a refactor exists for. | Guard engine → `guards/` |
| **Distinct change axis** | The code changes for a *different reason* or at a *different cadence* than its neighbours (SRP). "Where it lands" ≠ "may it move"; "who is allowed" ≠ "what the rule says". | Transition logic engine → `transition_logic/`; Authorization → `authorization/` |
| **Delegation seam** | A hand-off to another app — anti-corruption reads/writes across an app boundary. Everything the module consumes from elsewhere collects here. | Fact providers → `ports/` (engine app — see dependency direction below) |
| **Orchestration seam** | Use-case composition that wires the other layers together. One door per use case — deliberately *not* a plug-in surface. | Orchestration → `interactors/` |

A behaviour cluster with **no** signal firing is not yet a layer — leave it in the orchestrator
until a second reason to split appears.

## Dependency direction — who defines the ports (run before projecting the delegation seam)

The delegation seam can project two ways; the choice is a **dependency-direction** call decided by
stability (Stable-Dependencies Principle — arrows point at the more stable abstraction):

- **Engine-defines-ports** — the module is a *stable abstraction others plug into* (an engine, a
  mechanism). It DEFINES the port interfaces in its own app (`ports/` — interfaces only, imports
  zero other apps); the PRODUCER apps IMPLEMENT them as thin adapters in their own codebases; the
  GraphQL resolver injects the implementations (the codebase's native wiring). Arrows point
  apps → engine. Projected package: `ports/` (interfaces only). This is the exemplar's choice for
  `workflow_engine`.
- **Consumer-adapter** — the module is a *consumer* reaching stabler services. It writes adapters
  that import the producer's `app_interfaces/`. Arrows point module → producer. Projected package:
  `gateways/`.

Do NOT default an engine/mechanism to consumer-adapters (`gateways/` importing producers) — that is
the wrong arrow for a stable abstraction and pre-builds a cycle the moment the producer needs to
call back. When the delegation seam belongs to an engine, its Fact-providers pane says the module
*defines* the ports and producers *implement* them, and its projected package is `ports/`, not
`gateways/`. See `.claude/rules/clean-architecture.md` (Inter-App Communication) for the two modes.

## Gating policy, never domain math — the test for a centralized plug-in

An OCP surface (Guard engine) may centralize its plug-in classes in the engine app ONLY because
each plug-in is **thin**: read a fact → compare → return a verdict. That is gating *policy*, and
"what stops a move" is the engine's own domain. The moment a plug-in needs to **compute** a foreign
value (a fee shortfall, a rule predicate), the fix is a **new port** the owning app implements —
never a fatter plug-in that reaches into another app. Computing the fact stays in the owning app
behind a port; the plug-in only reads the port's verdict-fact.

- **No cross-app plug-in registration.** An owning app that truly owns a rule does not register a
  plug-in *into* the engine (reverse-dependency roulette) — it exposes a verdict-fact through a
  port instead, and a thin central plug-in reads it. With ports *implemented by the producers*
  (above), central plug-ins cost the engine zero app imports.
- This is the flip side of caution #3: caution #3 keeps *foreign axes* out of the surface; this
  test keeps *foreign computation* out of a plug-in on the surface.

## The 4 cautions — do NOT split when

1. **Splitting by file type alone.** "All the adapters" or "all the DTOs" is a filing cabinet, not
   a concern. A layer must own a *reason to change*, not a file type.
2. **One implementation, no second variant in sight.** An OCP surface needs a credible *second*
   plug-in. A registry with one entry is speculative structure — wait for the second reason.
3. **Letting the OCP surface absorb foreign axes.** The plug-in layer stays about its one axis.
   RBAC and destination resolution are *different* axes than guard evaluation — separate layers,
   not tenants of the guard engine.
4. **Turning an orchestrator into a second engine.** The orchestration layer *composes*; it does
   not re-implement predicate, rule, or fee math. A dynamic-rule guard delegates to `rules_engine`
   — the module never becomes a second rule evaluator.

## When a layer earns an L2 deep dive

Splitting a layer (above) and giving it a **deep dive** are different bars. A layer exists when one of the 4 signals fires; a layer earns an L2 deep dive (an ordered class map + decision cards) only when it is **decision-heavy** — design effort ∝ decision density, not surface area. Signals a layer is deep-dive-worthy:

- **It is an OCP surface** — a registry + contract + plug-ins, where the "how do variants get discovered / bound / evaluated" has real design in it (Guard engine, Transition logic engine).
- **It carries open design questions** — "context once per batch or per guard?", "fail-safe on an unknown config key?", "who parses the blob-buried type?". If you can name 2+ such questions, they become decision cards.
- **Its internal collaboration is non-obvious** — the order classes enter the run, and which class owns which decision, isn't inferable from the layer's one-line contract.

A layer does **NOT** earn a deep dive when it is CRUD, a pass-through read, or no-entity plumbing (Orchestration composes; Fact providers translate — neither holds a design decision). The disqualifier is blunt: **no decision cards → no deep dive.** A deep dive with an empty decisions section shouldn't exist — fold it back into the layer's side pane.

## Homing behaviours onto entities

Before layers settle, every behaviour must be homed on an entity:

- **Behaviour-homing test** — name the scope in the question; that's the host entity. A
  batch/plural question ("which transitions can this item take from this stage?") lives on the
  scope entity (Stage), not the subject (Transition). A singular question ("evaluate this
  transition") lives on the subject.
- **Signature litmus** — every behaviour is either *definition-time* (about the shape — no item in
  the signature, cacheable) or *item-time* (a decision about one item — item always present,
  usually inside a `context`). A signature that fits neither cleanly is two behaviours conflated;
  split it. A redundant param is allowed only as an explicit staleness assertion (e.g. passing the
  current `stage` so the call can assert the item hasn't moved).

## Output format for the pass

Render each layer as one line, then confirm with the user before the interface pass:

```
logical layer            →  signal fired        →  one-line rationale                            (projected: package/)
Orchestration            →  orchestration seam  →  composes the layers; one door per use case    (interactors/)
Authorization            →  distinct axis       →  authority ≠ business criteria; fail-closed     (authorization/)
Guard engine             →  OCP surface         →  add a guard variant without touching the core (guards/)
Transition logic engine  →  distinct axis       →  "where it lands" changes for other reasons     (transition_logic/)
Fact providers           →  delegation seam     →  engine defines the ports; producers implement  (ports/)
```

In the HTML blueprint this becomes the Pass-1 layer-stack diagram (one picture), with the
"question it answers · nature · hard boundary · projected package" for each layer living in its
side pane — never as a table on the page.

## Rules

- **Layers before folders** — name concerns; the package projection is a deferred pane note.
- **Derive, don't invent** — every layer must trace to homed behaviours. If a layer has no
  behaviour behind it, cut it.
- **An OCP surface must trace to a *confirmed* change axis** — the extension point exists because
  the user confirmed that variant grows (the architect's Phase-1c KPI: cost of the next likely
  change). A registry built for a speculative axis is the caution-#2 trap — wait for the second
  reason. When you draw an OCP-surface layer, be able to state the next-addition cost; if you
  can't, the OCP claim is decoration.
- **Confirm the pass** — surface the `layer → signal → rationale` lines as plain text and get
  agreement before laying out the interface.
