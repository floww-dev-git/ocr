# Design — YAML as the source of truth for task breakdowns

> **FORMAT UPDATE (2026-07-10):** switched JSON → **YAML** for readability and ONE format across
> tasks + reviews. Task **IDs must be quoted strings** (validator enforces — YAML coerces `2.10`→`2.1`).
> Parser: **PyYAML**. Shipped in commit `9da609c8ec`. The JSON-vs-markdown reasoning below is kept as
> the decision record; wherever it says JSON / `.json`, read YAML / `.yaml`.

**Author:** dhruva · **Date:** 2026-07-10 · **Status:** Draft (awaiting user review)
**Owner of encoding:** dhruva (all `.claude/` config + a new script)

## Problem

The tasks file is the most *frequently written* artifact in the pipeline (a tick per task) and
the most *frequently read* (every executing agent reads the spec). Today it is markdown, and
two costs stack:

1. **Per-tick re-read toll.** The single-writer rule says "re-read before every edit"; ticking a
   task means re-reading the whole ~120-line file. A 15-task slice burns ~27K tokens in re-reads.
2. **LLM does mechanical writes.** Flipping `[ ]→[x]` via an LLM Edit reproduces the exact dense
   task line (~150 tokens) when a script could do it for ~20.

Root cause: the markdown format makes structured edits (tick / add / reorder / query) an
LLM-and-regex job instead of a deterministic script job.

## Decision (settled with the user, 2026-07-10)

- **JSON is the single stored artifact.** No persisted markdown view — a persisted view would
  add a generator, a sync discipline, double git diffs, and drift risk, to buy only *pleasant
  human skimming* (minor: humans read the Gate-3 digest + `/feature-status`, not the raw file).
  A readable view is rendered **on demand** via `tasks.py view` (terminal, never stored).
- **The agent authors JSON directly** (a clean `Write`), validated the instant it lands. No
  markdown-authoring-then-parse step, so **no parser component**.
- **Additive rollout.** New features use JSON tooling; existing markdown features keep the current
  hooks/flow untouched until they finish. No tool carries dual-format logic. REF-001 stays
  markdown to completion (zero risk to its live S2 work).
- **Comprehension note (honest):** the earlier claim "LLMs read JSON worse than markdown" was
  *overstated* — a capable model reads well-labelled JSON fine, sometimes better for field
  lookup. JSON is only *more verbose* (token cost). The JSON-only decision rests on the
  redundancy/drift argument, not on comprehension.

## The schema

One JSON file per module (same naming as today, `.json` extension):
`<app>/docs/features/<slug>/tasks/tasks-ADR-NNN-<name>[--module].json`

### Feature-level (once per file)

```jsonc
{
  "adr": "workflow_engine/docs/features/<slug>/adrs/ADR-003-....md",
  "module": "workflow_engine",              // omit for single-module
  "what": "class-4 no-stories WHAT (optional)",
  "tasks": [ /* see below */ ],
  "carried_flags": ["... surfaces at 3.2"],
  "decisions": [{ "chosen": "steel thread = 2.0", "over": "...", "because": "..." }]
}
```

`ordering` and `parallel` are **computed** from per-task `depends_on`, never stored.
`relevant_files` and `pins` (REF-001-era) are **dropped** — per-task `outcome`/`artifacts`
make a top-level file list redundant. `siblings` is **dropped** — the other module files are
globbed from the `tasks/` folder by the shared `tasks-ADR-NNN-<name>--*.json` prefix (the
naming convention already gives you the set; storing it would just drift).

### Per-task object (flat list; slice membership derives from id prefix)

```jsonc
{
  "id": "2.1", "type": "task", "status": "todo",   // type ∈ slice|foundation|task|composition|refactor
  "outcome": "Write CreateABCInteractor",          // crisp deliverable
  "user_stories": ["US-1"],                         // traceability
  "depends_on": ["2.0"],                            // dependency graph → computes ordering+parallel
  "inputs":  "CreateABCDTO { entity_id, name }",    // contract IN
  "output":  "ABCResultDTO { entity_id, status }",  // contract OUT
  "outline": "validate admin → build DTO → storage.create → return DTO",  // ROUGH sketch
  "cases":   ["happy (AC-1)", "not admin → error (AC-2)", "missing id → NotFound (Err-1)"],
  "size": "S", "tier": "judgment",                  // feed model-routing + parallelism
  "artifacts": ["abc/interactors/create_abc.py", "CreateABCInteractor"],  // tick-evidence checks these
  "commit": null                                    // CLI sets the hash at commit time
}
```

**Field rationale (why each machine field survives):**
- `id` + `status` — the keys the CLI ticks by; the whole point.
- `type` — a **slice** closes with an integration suite; `foundation`/`composition` don't. Id
  number alone can't distinguish them. Behaviourally load-bearing.
- `depends_on` — makes dependency-first ordering machine-checkable, lets the coordinator
  **compute** parallel tracks (no hand-authored `∥`), and **subsumes** the old `demanded_by`
  citation: an orphan contract is simply a task nothing depends on.
- `size` + `tier` — the task-coordinator routes the worker model by `tier` and spawns teams by
  `size` (the model-routing policy).
- `artifacts` — tick-evidence lets a task reach `done` only if a real file/symbol exists
  (guards the 2026-07-02 false-tick bug). May be **derivable** from `outcome`+`output`.
- `commit` — auto-set; turns the push-gate commit-series into a query.

**Bar for the `outline` field:** a developer must be able to execute the task from its fields
alone. The outline is rough, but `inputs`+`output`+`cases`+`outcome` carry the contract — if a
dev would have to re-open the ADR to proceed, the outline is too thin.

## The CLI — `.claude/scripts/tasks.py`

The agent authors the JSON with a direct `Write`. The CLI owns every **edit and read** after that:

| Command | Purpose | Frequency |
|---|---|---|
| `tick <file> <id>` / `untick` | flip `status` done/undone | **high** (the token saver) |
| `set-status <file> <id> <s>` | todo \| in_progress \| done | med |
| `add <file> --after <id> --json '<obj>'` | insert a task (design correction) | rare |
| `reorder <file> ...` | re-sequence / renumber | rare |
| `status <file>` · `progress <file>` | % done (raw + size-weighted) for `/feature-status` | on read |
| `series <file>` | the commit series from `commit` fields (push gate) | per plan |
| `view <file>` | render a markdown checkbox view to the terminal | on demand |
| `validate <file>` | schema + tick-evidence + ordering | on demand / CI |

The coordinator (sole writer) calls `tick` via Bash (~20 tokens) instead of an LLM Edit.

## Validation — one module, two entry points

`check_tasks_json.py` holds the validation logic: **schema** · **tick-evidence** (a `done` task
has ≥1 real artifact) · **ordering** (`depends_on` acyclic + dependency-first). It runs from:

1. **PostToolUse hook on `tasks-*.json`** — fires when the agent `Write`s/`Edit`s the JSON
   directly (authoring + rare adds). Fail-closed.
2. **Inline in `tasks.py`** — every CLI write re-runs it before saving (CLI writes are Bash, so
   PostToolUse does not fire on them). Same module, so no divergence.

The two existing hooks (`check-tick-evidence.py`, `check-task-ordering.py`) are **untouched** —
they keep guarding in-flight markdown features. New JSON features are guarded by
`check-tasks-json.py`. No dual-format branching anywhere.

## Scope of changes

```
NEW
  .claude/scripts/tasks.py                     the CLI
  .claude/hooks/check-tasks-json.py            PostToolUse validator (+ CLI-imported module)
  skills/task-breakdown/references/tasks-schema.json   the schema + a filled example
  settings.json                                wire check-tasks-json.py (PostToolUse, matcher tasks-*.json)

EDITED (point NEW features at JSON; markdown path stays for OLD)
  skills/task-breakdown/SKILL.md               author tasks-*.json; grammar → field mapping
  skills/task-breakdown/references/tasks-file-template.md   → JSON template
  agents/task-coordinator.md                   tick via `tasks.py tick`, not an Edit; sole-writer holds JSON
  rules/dev-loop.md · references/agent-teams-pipeline.md    ticking → tasks.py
  rules/references/feature-folder.md           tasks/ holds .json
  rules/feature-context.md                     active pointer → tasks-*.json
  skills/feature-status/SKILL.md               progress from `tasks.py progress`

UNTOUCHED (additive rollout)
  hooks/check-tick-evidence.py · check-task-ordering.py     stay for OLD markdown features
```

## Phased rollout (blast radius is large — land in order, each independently testable)

1. **Foundation** — `tasks-schema.json`, `check_tasks_json.py` (validator module), `tasks.py`
   with `validate`/`view`/`status`/`progress`. Self-test on a hand-written example JSON. No
   pipeline wiring yet — nothing depends on it.
2. **Write ops** — `tick`/`untick`/`set-status`/`series` in `tasks.py`; wire the PostToolUse
   hook. Test on the example.
3. **Authoring** — rewrite `task-breakdown/SKILL.md` + template to emit JSON; the schema doc is
   its contract. First NEW feature exercises it end-to-end.
4. **Coordinator + dev-loop** — task-coordinator ticks via `tasks.py`; sole-writer rule updated
   (holds JSON, targeted CLI writes). `feature-status` reads `tasks.py progress`.
5. **Adds/reorder** — the rare-op commands, once a design-correction case actually needs them.

Old markdown features ride the existing hooks untouched throughout.

## Open points (settle during planning)

- **`add` mechanics** — for the rare mid-flight add, does the agent author the task object and
  pass it to `tasks.py add`, or Edit the JSON directly + let the PostToolUse hook validate?
  (Multiline prose as a CLI arg is awkward; a temp-file or heredoc may be cleaner.)
- **`artifacts` derivation** — hand-authored, or derived from `outcome`+`output`+the test path?
- **`size`/`tier` weighting** in `progress` — reuse the existing `/feature-status` S=1/M=2/L=4.

## Non-goals

- Not migrating existing markdown features. Not building analytics/dashboards over tasks (if that
  need arrives, it rides this JSON for free). Not a persisted markdown view.
