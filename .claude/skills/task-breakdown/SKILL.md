---
name: task-breakdown
description: Break an approved plan — the ADR plus the user stories it serves — into a clean, module-organized task breakdown; slices grouped per module/epic, every task carrying its case list (depth follows decision density), every slice closing with an integration suite against its stories' acceptance criteria. Use when the user says "task breakdown", "break down the ADR", "generate tasks", "create task list from ADR", or "plan implementation" (legacy alias).
argument-hint: "[path to ADR file]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash(python3 .claude/scripts/tasks.py *)
---

# Task Breakdown

Break down: $ARGUMENTS

**Scope:** take the ADR and the user stories it serves, plan each module, and break the plan
into tasks per the contract below — organized module / epic (slice) → task, never a flat list.

## Scope: Implementation Details Live Here

The ADR deliberately excludes implementation-level details — they live here. Specifically, this plan owns:
- Exhaustive interactor class lists with per-class responsibilities and method signatures (the ADR only sketches the 3-5 core interactors as a preliminary outline)
- Communication contracts between layers (exact DTO shapes passed between layers)
- Adapter surface enumeration (method names, signatures)
- GraphQL mutation/query surface (field lists, input/output types)

- Byte-level specs (canonicalization format, serialization details)
- Full model Python code blocks
- Implementation sequence / phasing / task ordering

- Storage interface method signatures
- DTO field-by-field definitions and `@dataclass` shapes
- Constants/enum value lists (exact members like `PIPELINE_STAGE`, `PMU_ACTION_CONTROL`)

When generating the plan, derive implementation specifics from the ADR's architectural decisions — the ADR provides the "why" and "what shape", this plan provides the "what exactly" and "in what order". If the ADR marked Core Interactor Architecture as "Preliminary" with open questions, resolve those here by confirming actual adapter surfaces and code patterns.

## Process — map → per-module breakdown (parallel) → contract check

The decomposition is already done upstream — the ADR's Modules & App Ownership (§5) and
`**Declared modules:**` header name the modules; the stories map to epics. Do NOT re-derive it;
break down module by module against it.

1. **Read the ADR AND the user stories it serves** — ADR: Modules & Layers, Entities & Core DB, Infrastructure, Failure Handling. Stories (paths on the dispatch manifest): they supply each task's `Cases:` (ACs + error scenarios) and each slice's integration-suite targets. Load the touched apps' `CLAUDE.md`s and `.claude/rules/references/engineering-canon.md` (the ordering checks are its mechanical form)
2. **Frame the breakdown map ◆ "Go" gate** — ONE table, cheap, presented before any expansion:
   `module / its epics/slices (from the stories) → the cross-module contract seams it consumes/produces (from the ADR)`. Mark the first thin end-to-end path. The map is step 3's work order and step 4's checklist — a wrong map invalidates every parallel expansion, so this is where the user corrects course
3. **Break down module by module — parallel** — per module, ONE tasks file (naming in step 5), applying the slice grammar WITHIN the module:
   - (0) that module's refactoring debt — consult `<app>/docs/refactoring-backlog.md` (developers log out-of-fence smells there per their Mission #4); pull entries that BLOCK this plan into 0.R tasks and mark them resolved in the backlog when the plan ships; non-blocking entries stay banked → (1) its models & migrations (schema projection of ADR-designed entities ONLY) → (2) its DTOs & constants (pure data — NO ports; contracts wait for the slice that demands them) → (3) its slices in dependency order, the first thin end-to-end path first where it lives, each built consumer-first (the interactor drives out its contracts) → its presenters/GraphQL composition roots → event handlers
   - Slice sub-order — **consumer-first (outside-in)**: domain entities/value objects (pure python) → DTOs → the interactor(s) (the CONSUMER — built and unit-tested FIRST against an autospec mock of the interface it drives out, together with any engines/strategies/guards it composes, each per its ADR § / decision card) → the storage interface (exactly the methods the interactor demanded) → storage implementation → integration suite (the slice CLOSER, wiring the real impl — see contract). **Build-once**: the interactor is NOT rewritten when the real storage lands — the mock-tested interactor is the same one the closer wires to the real collaborators. The interface EMERGES from the consumer, so every method has a consumer by construction (`check-dead-contracts` blocks any that don't). Engines emerge per-slice, never a pre-slice parent. Unit tests ride each sub-task's RED stage (dev-loop)
   - Cross-module seams: the CONSUMING module's slice carries the contract-demanding task; the PRODUCING module carries the implementation task — both cite the same seam row from the map
   - Module breakdowns are mutually independent by construction (own file, seams frozen in the map) — **author them in parallel** when >1 module (one background worker per module; single-writer per file). Deep sub-task detail only for decision-heavy engines; CRUD/pass-through behaviours get one task-line each (architect framework #9)
4. **Contract-integrity check — the merge step, after ALL modules land.** Verify the seams survived the parallel expansion, against the step-2 map:
   - every seam has BOTH sides tasked — a defining task (the engine-side contract, citing its demand) and a producing task (implements it), definition before implementation across files (merge-step check)
   - no orphan contracts — every interface/port task has a consuming task somewhere in the set
   - story coverage — every story serves exactly one slice across all files; none dropped, none doubled
   - fence — the UNION of all files' paths ⊆ the ADR's `**Declared modules:**` dirs
   - the primary file's Ordering & Parallelism footer records cross-FILE ordering + `∥` pairs
   A failed check is fixed before presenting — never shipped as a carried flag
5. **Save** — into the feature folder's `tasks/` subdir (layout per `.claude/rules/references/feature-folder.md`) as **YAML conforming to `references/tasks-schema.yaml`**: single-module plan: `<owning_app>/docs/features/<feature-slug>/tasks/tasks-[adr-file-name].yaml`. Multi-module: `tasks-[adr-file-name]--[module].yaml` per module in the same folder, each self-contained (its own `module:` scope + `carried_flags`/`decisions`). The tasks files are the ONLY home of the breakdown; if the ADR contains build-order or task-list content, flag it for removal (via `/create-adr` rewrite), don't mirror it. On save the `check-tasks-yaml.py` PostToolUse hook fires per file (the `tasks-ADR-*.yaml` pattern) and runs `tasks_lib.validate_all()` — schema + tick-evidence + dependency-ordering + slice-naming
6. **Cross-link** — every tasks file carries its source ADR in the `adr:` field; add/refresh the `**Implementation plan:** [path(s)]` pointer line in the ADR's header block listing EVERY tasks file (`.yaml` paths only, never task content)
7. **Validate** — run `python3 .claude/scripts/tasks.py validate <file>` per saved file and fix any finding before presenting (the `check-tasks-yaml.py` PostToolUse hook runs the same `validate_all` on save)

## Output Format

Author the file against `references/tasks-schema.yaml` — the field-by-field contract for the
YAML shape; don't hand-derive it. One `feature` object per file: `adr` (path) · optional
`module` / `what` · `tasks[]` · `carried_flags[]` · `decisions[]`. Each `tasks[]` entry carries
`id` · `type` (slice/foundation/task/composition/refactor) · `status` · `outcome` ·
`user_stories[]` · `depends_on[]` · `inputs` · `output` · `outline` · `cases[]` · `size` ·
`tier` · `artifacts[]` · optional `commit`. The schema's `$comment`s teach each field once — the
contract below owns the authoring rules. `python3 .claude/scripts/tasks.py view <file>` renders a
readable markdown view (with the computed Sequence / Parallel ordering); `tasks.py progress`
gives the raw + size-weighted %.

## Tasks-File Contract

- **`type: slice` = one vertical slice**, its `outcome` a caller-nameable behaviour ("attach an item to a stage", never "Storages"), its `outline` carrying the ADR pointer `(ADR §N)` — the developer reads ONE ADR section per slice, never the whole ADR. Its `N.x` leaf tasks `depends_on` it.
- **Write it clearly. Who reads it doesn't change the bar.** Anyone opening a task — a developer agent, a reviewer, a new joiner, you a week later — must know what it means without decoding a metaphor or opening the ADR first. Clarity is not a courtesy extended to humans: a metaphor costs an agent the same inference and the same chance of resolving it wrong, and a 2,000-char outline costs it the same attention. If a sentence needs insider vocabulary to parse, it is the wrong sentence — see **Plain words** below. *(Amended 2026-07-16, user ruling: removes "this file is written for the executing agent — the human reviews the Gate-3 digest, never this file". That line changed no rule, but it read as permission to be insular — a lower bar because nobody's watching. There is no lower bar.)*
- **One field, one job — see the template below.** `outcome` = what becomes true; `inputs`/`output` = the signature (types in, type out); `outline` = the approach, only the non-obvious part; `artifacts[]` = the ✔ evidence (real paths / symbols a test can assert on); `cases[]` + `user_stories[]` = the AC trace. *(Amended 2026-07-16: this previously read "`output` + `outline` = WHAT + WHERE + the exact semantic" — but `outcome` already owned WHAT and `output` owned WHERE, so `outline` was instructed to duplicate two sibling fields. Only "the exact semantic" survives, e.g. "is-not-None guard on update vs default-fallback on create" spelled out.)*
- **WHAT lives here; WHY lives in the ADR — and they never swap.** A task is executable without opening the ADR: `outline` tells the developer exactly what to do and where. It does NOT explain the reasoning behind it — that is the ADR's only job, and you link it (`see ADR §N`), never paste it. If a task seems to need its WHY explained inline, that is the signal to link the ADR section, not to grow the `outline`. *(Amended 2026-07-16: this contract previously said "if understanding a task requires reading the ADR, sharpen its `outline`" while Hard Check 5 said "don't repeat the ADR's reasoning — link it". Those fight, and the architect obeyed both — 986-char average outlines that explain AND cite. WHAT-here/WHY-there resolves it.)*
- **Every task carries a `cases[]` list; depth scales with how many judgment calls the task holds.** It lists what to check and test — happy path · failure paths · edge cases — each traceable to an AC number or an Error-Scenarios row (no invented cases, no missed ones). The developer writes the failing tests directly FROM this list — never re-derives them from the code. Judgment-dense tasks (the main use-case interactor, engines, non-obvious semantics) spell out every case with its exact behaviour; mechanical/CRUD tasks get one compact case (still AC-traced — `cases[]` is empty only for a `slice` parent, `composition`, or `refactor` row).

### Plain words (hard rule)

Load `.claude/rules/references/plain-language.md` and write every field by it. Assume the reader is a **non-native English speaker** and an **SDE-1**, and has not read this feature's ADR.

- **Name the thing, don't nickname it.** Write `ExecuteTransitionInteractor` or "the interactor that runs a transition" — never "the door". Write "someone tries to move an item" — never "a press". A feature-local metaphor is unreadable to everyone who wasn't in the room when it was coined. *(Measured 2026-07-16 across REF-001's 8 files: "the door" ×54, "a press" ×20, "the walk" ×17 — none defined anywhere a reader could find.)*
- **Project vocabulary with a defined home is fine** — "slice", "integration closer", "consumer-first" are defined in `dev-loop.md` / `engineering-canon.md`. The test isn't "is it a term?", it's **"can the reader look it up?"**
- **One idea per line. Short sentences.** If a sentence needs a fancy word to sound right, rewrite the sentence.

### The task template — one field, one job

**Every field owns exactly one thing, and no two overlap.** The caps below aren't arbitrary limits; they're what falls out once the duplication is gone. A field that grows past its budget is almost always answering another field's question.

```yaml
- id: '2.1'
  type: task
  status: todo
  outcome: Block a move when the item's fields fail validation
  user_stories: [US-3]
  depends_on: ['1.2']
  inputs: [TransitionContext, FieldCriteriaConfig]
  output: FieldCriteriaGuard
  outline: Read the criteria from ctx.payload, not from storage — the values this
    caller submitted, not the saved ones. See ADR-006 §D3.
  cases:
    - fields fail validation -> blocked, naming the exact fields (US-3 AC1)
    - fields pass -> guard returns met (US-3 AC1)
  size: S
  tier: judgment
  artifacts: [workflow_engine/guards/field_criteria_guard.py]
```

| Field | Owns | Budget | Fails if |
|---|---|---|---|
| `outcome` | what becomes true when done | ~120 | not verb-first · em-dash elaboration |
| `inputs` | **the types the code consumes** | type names | a path · a doc · a task id · a sentence |
| `output` | **the type it produces** | ~120 | a path · a description |
| `outline` | the approach — the non-obvious part only | ~900 (all sizes) | repeats outcome/output · explains WHY · sprawls |
| `cases` | what to test | one per RED cycle | not AC-traced |
| `artifacts` | proof it exists (paths) | — | — |

### `inputs` / `output` are a SIGNATURE, not a reading list

`inputs -> task -> output`. `inputs` names the **types this task's code consumes**; `output` names the **type it produces**. Paths live in `artifacts` — the field the tick-evidence check actually reads.

```yaml
# NO — a bibliography. Every entry restates a sibling field.
inputs: The guards 1.1/1.2; the built door `workflow_engine/interactors/execute_transition.py`
  + its `TransitionBlocked`; ADR-006 §D3; US-3's ACs
output: '`workflow_engine/guards/field_criteria_guard.py`'

# YES — a signature. New information, nothing restated.
inputs: [TransitionContext, FieldCriteriaConfig]
output: FieldCriteriaGuard
```

**Nothing is lost, because the bibliography never had unique content** — every part of it already had a home:

| was in `inputs` | actually lives in |
|---|---|
| a prior task's file | `depends_on` |
| `ADR-006 §D3` | the top-level `adr:` + `outline`'s link |
| `US-3` | `user_stories:` |
| a path | `artifacts` |

*(Measured 2026-07-16 across REF-001's 77 tasks: `inputs` restated a `depends_on` id in 49%, the ADR in 75%, a `user_stories` id in 25% — and the paths it did carry were groping at types anyway: `dtos/guard_dtos.py` wanting to be `GuardResult`. The field was named like a signature and used like a bibliography.)*

A string `inputs`, or a path in `output`, still validates — the 8 REF-001 files predate this rule. Every NEW file authors the signature.
- **Every slice closes with an integration suite.** After the slice's units land (door, collaborators, storage), the final sub-task implements the integration test suite for the surface the slice exposes (GraphQL op / interface): one test per acceptance criterion of the stories the slice serves (`/write-integration-testcase`). The chain is greppable: slice → its stories → their flow steps → their ACs. A slice is not done until its stories are proven end-to-end — this suite is what fills the "proves" column of the Gate-3 slice table.
- **Module/epic organization:** multi-module plans set the file's `module:` field and order slices by `depends_on`; each `type: slice` task names the stories it serves in `user_stories[]`.
- **`size:` field** `S / M / L` — the axis is NOT file count: `S` = one RED→GREEN cycle (one test setup); `M` = 2-3 independent test setups, single app; `L` = must state its planned split in `outline`. HARD RULE: a task crossing an app boundary (e.g. bps + owning app + adapter round-trip) ALWAYS splits on the app seam regardless of file count — each side is independently testable per clean-architecture App Isolation. A mechanical fan-out through many files following one established pattern is still ONE task.
- **`tier:` field** `mechanical / judgment` — one per task. The axis is **reasoning density, not file count**: `judgment` = the main use-case interactor, engines, non-obvious semantics, novel design calls; `mechanical` = CRUD, pass-through reads, DTO/constant wiring, established-pattern fan-out. This is the input to per-task model routing — the task-coordinator spawns each worker at the tier's model (judgment → frontier, mechanical → cheaper; judging seats and consequence-bearing tasks are never cheapened). A task touching tenancy/gating/payments/auth is consequence-bearing — never tag it below the `mechanical` floor and it keeps security review regardless. When a task's tier is ambiguous, tag `judgment` — a wrong down-tier costs a rework cycle.
- **Top-level `carried_flags[]` and `decisions[]`** (primary file; per-module files carry `carried_flags` for their own scope):
  - **Ordering & parallelism is COMPUTED, not hand-written** — `tasks_lib.compute_ordering()` derives the dependency-ordered Sequence and the parallel (`∥`) layers from `depends_on` (a plain topological sort — it honours the authored dependencies, it does not impose a layer order); `tasks.py view` renders them. Populate `depends_on` correctly and the ordering footer writes itself. The orchestrator uses the computed parallel layers to decide whether to spawn a dev team (4+ independent tasks), after checking they touch different files — a hint, never blindly trusted.
  - `carried_flags[]` — open sign-offs/questions that must surface at a specific task's presentation.
  - `decisions[]` (primary file only) — the breakdown's judgment calls, one line each, `CHOSEN · OVER · BECAUSE` (steel-thread pick, non-obvious ordering, L-task splits; 3–6 typically). This is the CANONICAL text behind the Gate-3 decision cards and the feature's decision log — a decision that exists only in conversation can't answer a later "why this order?".
- **Ports note:** port interfaces and the tasks that implement them go INSIDE the first slice that needs them — never a foundations parent. Consumer-first: the interactor task is built first and its `depends_on` names only the tier-1 collaborators it uses (enums/DTOs/exceptions — Django models are NOT here, they land with the storage impl); the storage interface, implementation (with its models), and integration closer `depends_on` the interactor's work, so the consumer precedes what serves it. The interface is exactly what the interactor demanded, so every method has a consumer by construction — `check-dead-contracts` blocks any that don't.

## Hard Checks (a plan that breaks these fails review)

Nine simple rules. The examples are just the common cases — apply the rule to new cases too,
and flag dhruva when one shows up so it gets added to the automatic checks.

1. **Consumer-first order.** Within each slice: **interactor(s) FIRST** — building the consumer
   drives out its **tier-1 collaborators, built WITH it**: enums/constants, DTOs, domain
   exceptions, the storage interface + service/port interfaces it calls (abstract — mocked in its
   test), and — `workflow_engine` only — the rich domain entities it uses (wired real) → then the
   **implementations** that satisfy those contracts: the storage implementation (the Django
   models + migration land HERE, with the storage impl — only it touches models; models are NEVER
   a first/foundation task), adapters, gateway → presenters → app_interfaces → resolvers (last) →
   integration closer. Encode this in `depends_on`: the interactor `depends_on` only its tier-1
   collaborators (enums/DTOs/exceptions); the storage interface, implementation (with its models),
   and closer `depends_on` the interactor's work. The interface emerges from the consumer, so
   every method has a consumer by construction. *(auto-checked: `tasks_lib.check_ordering` — the
   `depends_on` DAG rejects cycles, unknown deps, and done-before-dependency, and permits
   consumer-first by construction; a contract method with no consumer is caught at review, not by
   a hook — `check-dead-contracts.py` was deleted 2026-07-29 for a 50% false-positive rate)*
2. **Name tasks by what the user gets, not by code structure.** A `type: slice`/`foundation`
   `outcome` is a caller-nameable behaviour — never "Interactors" or "Storages". *(auto-checked:
   `tasks_lib.check_slice_naming` — layer-noun outcome denylist)*
3. **"Done" must be provable.** Every task's `artifacts[]` names a real file or symbol a test
   can assert on; a task may be `status: done` only if ≥1 artifact resolves. *(auto-checked:
   `tasks_lib.check_tick_evidence`; `tasks.py tick` is fail-closed — it refuses if revalidation
   fails)*
4. **Stay inside the ADR's declared modules.** Touching anything outside them is a scope
   change — go through the Design Correction Protocol; never quietly widen the plan.
5. **Don't repeat the ADR's reasoning — link it** (`see ADR §N`). One-line "don't undo this"
   warnings ARE welcome inline; explanations are not. WHAT lives in the task, WHY lives in the
   ADR — see the Tasks-File Contract. *(auto-checked, warn-level: `tasks_lib.check_readability`
   flags an over-budget `outline`, the usual sign that WHY leaked in.)*
6. **Plain words, no nicknames.** Every field readable by a non-native English speaker at SDE-1
   level who has not read the ADR. Name things (`ExecuteTransitionInteractor`); never coin a
   feature-local metaphor ("the door", "a press"). Project terms with a lookup-able home are
   fine. *(auto-checked, warn-level: `tasks_lib.check_readability` — undefined-metaphor denylist
   + the `plain-language.md` banned words.)*
7. **A wiring task's cases enter at the REAL front door.** When a task's `outcome` is "X now
   reaches Y" — a cutover, a re-point, any wiring change — at least one case must enter at the
   production entry point (the mutation/resolver, the SQS or Step Functions handler, the scheduler
   tick) and assert Y was reached. A case that starts at Y and proves Y behaves correctly does
   NOT prove anything reaches it. Name the entry point in the case text so the developer cannot
   satisfy it one layer in. *(Real case: relieve-v2 task 12.6 "moved both doors onto the new
   workflow" — its cases proved the v2 interactor published the right job, the mutation still
   imported the v1 interactor, and the slice passed with its headline outcome undelivered. Same
   class as an earlier miss on the same feature: an interactor calling a boundary method that did
   not exist, green because the test stubbed the missing port. Both are "the seam was never
   crossed by a test".)*
8. **A blocker is a `depends_on` edge, never a sentence.** If task A cannot be built until task B
   lands, that is `depends_on: ['B']` — full stop. A blocker written in prose ("BLOCKED IF STEP 6
   HAS NOT LANDED") is invisible to the ordering check, so the plan validates, the queue orders A
   before B, and the slice closes approved with an unbuildable task inside it. Cross-step
   blockers are the sharp case: the `depends_on` id must name the other step's task even when the
   files differ. *(auto-checked, warn-level: `tasks_lib.check_readability` — prose-blocker
   denylist. It flags the FORM; the fix is always the same edge.)*
9. **Validate every file before presenting:**
   `python3 .claude/scripts/tasks.py validate <file>` must print `OK`.

## Interaction

Two pauses — and at both, the human reviews DECISIONS, never raw task text (upstream gates
already approved the content; hooks check the grammar; the file is the executing agent's copy).

**Pause 1 — the breakdown map (Process step 2):** module → slices → seams, the first thin end-to-end path marked;
wait for "Go" before any per-module expansion (a wrong map invalidates every parallel worker).

**Pause 2 — the Gate-3 digest (after the step-4 contract check).** One screen, five blocks:
1. **The map, ✓'d** — the same table from Pause 1, now carrying the contract-check ✓s.
2. **Decision cards** — rendered from the primary file's `## Decisions` footer (steel-thread
   pick, non-obvious ordering, L-task splits), each as *CHOSEN X · OVER Y · BECAUSE Z* —
   veto-able at a glance. Only genuine decisions; typically 3–6 cards, never one per task.
   The cards also land on the **decision log** — the `#/decisions` sub-page of the living
   review page (see `intake-requirement/references/review-page.md`).
3. **Slice table** per module: `slice · serves US-x · proves (its integration suite) ·
   #tasks · size chips`. "Proves" doubles as the slice-completion definition.
4. **⚠ Attention flags** — machine-surfaced, human-judged: any `L` task · any slice with 8+
   sub-tasks · story coverage resolved by judgment call · the widest cross-module seam. The
   reviewer's eye goes where the risk is, even on a 30-second skim.
5. **Not doing** — deferrals + carried flags, explicit (the most veto-prone list).
Approve via `AskUserQuestion`; tasks files linked for spot-checks (prerogative, not
obligation). The living review page gains this digest as its Gate-3 pass.
