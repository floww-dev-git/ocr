# Engineering Canon — Load-on-Demand Reference

## WHY this file exists (and why it is NOT a rule)
The model knows these principles; every violation we've recorded was a *retrieval-at-the-decision-point*
failure, not a knowledge gap. So the canon loads exactly where decisions happen (see Loaders) and costs
zero always-on context. A principle's name is a **lookup key in the process, never decoration in an
artifact** — the create-adr pattern-name ban stands. Every entry cashes out as a planning consequence
and a review invariant; an entry that can't state both doesn't get in. Project rules
(`clean-code.md`, `clean-architecture.md`, etc.) stay the source of truth — entries point, never duplicate.

## Loaders
| Who | Loads at |
|---|---|
| architect | Phase 1 (design) and before ADR/plan authoring |
| developer | Before starting a multi-task plan (not per bug fix) |
| reviewer | Start of a structured review |
| `create-adr` · `task-breakdown` · `design-module` | Hard-check step |
| `review-pr` · `self-review-checklist` | Checklist step |

## The Three Laws (the canon compressed)
1. **Build consumer-first (outside-in)** — the consumer (the interactor) is built and unit-tested FIRST; the act of writing it drives out the exact storage/port methods it needs, and those methods ARE the interface. The interface is written to match, then the implementation. The interactor is tested against an autospec mock of the interface it drove out — **build-once**: it is NOT rebuilt when the real storage lands; only the integration closer wires the real implementation. Per-slice order: **interactor(s) FIRST** — building it drives out its **tier-1 collaborators, built WITH it**: enums/constants, DTOs, domain exceptions, the storage interface + service/port interfaces it calls (abstract — MOCKED in its test), and — `workflow_engine` only — the rich domain entities it uses (behaviour-carrying, wired REAL in its test) → **implementations** that satisfy those contracts: the storage implementation (and the Django models + migration land HERE, with the storage impl — only it touches models, never first), adapters, gateway/reconstitution → presenters → app_interfaces → resolvers (LAST) → integration closer (real DB + real wiring). Test rule: MOCK the I/O contracts (storage/port interfaces), wire REAL the pure-logic collaborators (DTOs, rich entities). (Amended 2026-07-11, user ruling: **reverses** the 2026-07-04 dependency-first/door-last amendment — pre-declaring interfaces with demand-citations was needless overhead; per Clean Architecture / GOOS the interface EMERGES from the consumer.)
2. **The consumer owns the contract** — at every seam, the consumer defines the interface; nothing exists that no consumer demands. Ownership is proven by the consumer being built FIRST and actually calling the method — an interface method with no consumer is caught at review, not by a hook *(`check-dead-contracts.py` deleted 2026-07-29, 50% false-positive rate)* — never by a textual demand-citation.
3. **Knowing ≠ following** — principles live down the enforcement ladder: hooks > skill hard-checks > persona prose. Prose is where a principle *waits* for promotion.

---

### SRP — Single Responsibility (Martin)
- **Canon:** a module has one reason to change — one actor it answers to.
- **Planning:** each task delivers ONE responsibility; an interactor is one use case (`interactors.md`: one public method).
- **Review:** can you name the single actor a class serves? Two actors = split.
- **Enforcement:** prose (`clean-code.md` limits are the proxy: 50-line functions, 500-line files).

### OCP — Open-Closed (Meyer/Martin)
- **Canon:** open for extension, closed for modification — along *confirmed* change axes only.
- **Planning:** architect Phase 1c: identify axes, ASK to confirm, design extension points only for confirmed ones, prove the cost in the ADR's Extension Cost section.
- **Review:** does the next likely addition require zero core edits? Is the extension point on a confirmed axis (else YAGNI violation)?
- **Enforcement:** prose — architect extension-cost KPI; create-adr §12 requires the cost statement.

### LSP — Substitutability (Liskov)
- **Canon:** a subtype must honour its base type's contract — no strengthened preconditions, no surprise side effects.
- **Planning:** registry/strategy designs (guards, transition strategies) define ONE base contract all members satisfy.
- **Review:** can any registered implementation be swapped without the engine caring? A strategy that needs `isinstance` checks in the engine fails.
- **Enforcement:** prose.

### ISP — Interface Segregation (Martin)
- **Canon:** no client should depend on methods it does not use.
- **Planning:** storage interfaces accrete from consumer demand — never from tables (`storages.md`, task-breakdown Hard Checks).
- **Review:** every interface method has a consuming interactor call site (reviewer item 11).
- **Enforcement:** reviewer item 11 (prose). *(The `check-dead-contracts.py` hook was deleted 2026-07-29: measured against 30 committed `storage_interfaces/` files it rejected 15 — a 50% false-positive rate, because its consumer detection greps `.method(` under `*interactors*`/`*app_interfaces*` and misses dynamic and out-of-glob call sites. A guard that rejects half of working code trains people to ignore it.)*

### DIP — Dependency Inversion (Martin)
- **Canon:** high-level policy depends on abstractions; details depend on the same abstractions.
- **Planning:** the interactor is built first and drives out the interface it demands; the interface precedes its implementation (consumer-first).
- **Review:** interactors type-hint abstract interfaces only (`interactors.md`); no concrete storage in a constructor signature.
- **Enforcement:** `check-tasks-yaml.py` (`tasks_lib.check_ordering` — the depends_on DAG); `quality-gate.sh` cross-app grep.

### SDP/SAP — Stable Dependencies / Stable Abstractions (Martin, component)
- **Canon:** depend in the direction of stability; the stable thing is the abstract thing — and the abstract thing wears NO domain vocabulary.
- **Planning:** an engine (stable abstraction others plug into) DEFINES its ports; producers implement them — arrows point apps → engine (`clean-architecture.md` mode 2). Scope those ports to the engine's OWN boundary needs (tenancy, a command to a system it doesn't own), not to producer facts: "engine owns the mechanism, producers own the domain plug-ins" beats "engine defines fact ports it pulls through" whenever the domain axis is wide. N fact ports for N domain facts is the halfway house — collapse to a generic context + producer-registered plug-ins that read their own storages.
- **Review:** reviewer item 10 — flag consumer-adapters (`gateways/`) inside a stable abstraction; AND flag domain vocabulary in the engine core plus a growing fact-port count (each producer fact behind its own port = the guard belongs in the producer). Fact-port count is a design smell, not a metric to optimize.
- **Enforcement:** reviewer item 10 + the engine-domain-purity review line; `quality-gate.sh` cross-app import grep. Canonical: REF-001 `plugin-architecture.md` — 19 ports → 2.

### CCP/CRP — Common Closure / Common Reuse (Martin, component)
- **Canon:** what changes together lives together; don't force consumers to depend on what they don't reuse.
- **Planning:** app ownership follows the change axis — the app that changes when the rule changes owns the module (`configio-architecture.md` owning-app doctrine).
- **Review:** does a change to one concern force edits across apps? Wrong closure.
- **Enforcement:** prose.

### CA Dependency Rule (Martin, Clean Architecture)
- **Canon:** source-code dependencies point only inward — domain knows nothing of frameworks or delivery.
- **Planning:** interactors get zero Django imports; framework touches only models/storages/presenters (`interactors.md`, `clean-architecture.md`).
- **Review:** any `from django` or ORM object inside `interactors/` fails.
- **Enforcement:** `quality-gate.sh` cross-app + framework greps.

### Consumer-first construction (GOOS / Clean Architecture — Freeman/Pryce)
- **Canon:** the consumer drives out its collaborators and contracts BY being built first. Write the interactor, discover the storage/port methods it needs, and those methods ARE the interface. Unit-test the interactor against an autospec mock of that interface (**build-once** — no rewrite when the real impl lands); the implementation and the integration closer (which wires the real impl) follow.
- **Planning:** slice 1 is the first thin end-to-end path; within a slice: interactor(s) FIRST — driving out its tier-1 collaborators built WITH it (enums/constants, DTOs, domain exceptions, the storage + service/port interfaces it calls [mocked in its test], and — `workflow_engine` only — the rich domain entities it uses [wired real]) → implementations (storage impl + its Django models & migration, adapters, gateway) → presenters → app_interfaces → resolvers (last) → integration closer.
- **Review:** was the interactor built and mock-tested first against the interface it demanded? Does every interface method have a real consumer? A method no consumer calls is an orphan.
- **Enforcement:** `check-tasks-yaml.py` (`tasks_lib.check_ordering` — the depends_on DAG rejects cycles / unknown deps / done-before-dependency and permits consumer-first by construction; `check_slice_naming` — no layer-noun slice/foundation parents); `check-dead-contracts.py` at write time (an interface method with no consumer is blocked).

### Red-Green-Refactor (Beck)
- **Canon:** write the failing test first, make it pass minimally, then refactor on green.
- **Planning:** dev-loop stages are TEST-FIRST → IMPLEMENT → REFACTOR (see `dev-loop.md`); a task's ✔ criteria seed its first failing test.
- **Review:** test commits/files exist for every unit; tests assert behaviour, not implementation internals.
- **Enforcement:** dev-loop skill stage order (hard check); `reviewer` test-existence Critical finding.

### Walking Skeleton (Cockburn)
- **Canon:** build the thinnest end-to-end slice first; grow the system by widening a working spine.
- **Planning:** `design-module` slices by user flow and locks slice 1 (the first thin end-to-end path) before designing slice 2.
- **Review:** is there a working end-to-end path before breadth work begins?
- **Enforcement:** prose — design-module slice-first sequencing.

### Vertical Slicing / INVEST (Jacobson; Wake)
- **Canon:** a slice is a caller-nameable behaviour — independent, valuable, testable — never a layer.
- **Planning:** task parents are use-case slices ("Slice: Attach Item"), not layer collections ("Interactors").
- **Review:** can a caller name the behaviour a task delivers? Layer-noun titles fail.
- **Enforcement:** `check-tasks-yaml.py` (`tasks_lib.check_slice_naming` — slice/foundation layer-noun denylist).

### YAGNI (Beck)
- **Canon:** don't build it until something real demands it.
- **Planning:** contracts grow only by consumer demand; extension points only on confirmed axes; create-adr Exclusion List bars speculative surface.
- **Review:** every method, DTO field, and abstraction has a current consumer. Speculative "for later" code fails.
- **Enforcement:** prose (create-adr exclusion list) + reviewer item 11 for interfaces. *(`check-dead-contracts.py` deleted 2026-07-29 — 50% false-positive rate; see the ISP entry.)*

### Law of Demeter (Lieberherr)
- **Canon:** talk to your friends, not to strangers — no reaching through object chains.
- **Planning:** DTO shapes give consumers what they need directly; no `a.b.c.d` traversal designs.
- **Review:** chained attribute walks across layer boundaries fail (`clean-code.md`).
- **Enforcement:** prose (`clean-code.md`).

### Tell-Don't-Ask / DRY (Hunt/Thomas)
- **Canon:** ask an object to do the work rather than interrogating its state; every fact has one home.
- **Planning:** inside `workflow_engine/`, behaviour lives ON the domain entities (`rich-domain-models.md`, scoped); shared utilities are wired into ALL call sites in the same PR.
- **Review:** logic duplicated across the changeset fails; state interrogation that should be a domain method fails (in-scope apps).
- **Enforcement:** prose (`clean-code.md` DRY section; `rich-domain-models.md` scoped).
