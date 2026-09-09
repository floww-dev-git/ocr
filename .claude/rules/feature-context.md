---
globs:
  - "**/feature-context.md"
---

# Feature Context File

## Location (canonical)

`<owning_app>/docs/features/<feature-slug>/feature-context.md` — **tracked in git**, at the top
level of the feature's docs folder (full layout + naming: `.claude/rules/references/feature-folder.md`).
The slug matches the branch: `feature/<slug>`. One context file per feature; the file lives ON
the feature branch, so on a single checkout (no worktrees) a branch switch automatically swaps
in the right context. Multi-app features keep ONE home — the primary owning app. A repo-root
`feature-context.md` is legacy (gitignored); tools fall back to it only when no feature-folder
copy exists.

## What It Maintains

A resume note, not a mirror. The feature folder has fixed names and the tasks file owns task
state, so feature-context keeps ONLY what has no other home:

- **Header** — feature name + branch (readable; both derivable from git + folder, not load-bearing).
- **Phase + next gate** — where in the pipeline the feature sits, e.g. `C · Build — next gate: PUSH ◆4`. Recorded nowhere else.
- **Active pointer** — one line per in-flight track: `<tasks-file> → task N.N (Slice: …) · stage · open findings`. Points AT the tasks file, never copies its lines. The stage (RED/GREEN/REVIEW) and open-finding count are the unique part — they aren't in the tasks file. Parallel tracks each get their own line.
- **Stories served** — the epic file(s) + US-ids this feature draws from: `stories: <owning_app>#<epic-slug>#US-1..4, <owning_app>#<epic-slug-2>#US-10`. Stories live at `<owning_app>/docs/user_stories/`, NOT in the feature folder — this line is the feature's only pointer to them.
- **Notes for next session** — free-form handoff: what's next, gotchas, any operational blocker (env down / waiting on user / an unresolved T-trip).

## What Lives Elsewhere (never mirror here)

- **Task list · completed/pending · status** → the `tasks-ADR-*.yaml` file (hook-protected; `/feature-status` reads its task `status` fields for %-done).
- **PRD / flows / ADR / tasks paths** → the folder convention (`prd.md`, `flows.md` are fixed names; the ADR is reached via the active tasks file's header link; the tasks file is named by the Active pointer). **Stories are NOT in the folder** — they live with the owning app, one file per epic: `<owning_app>/docs/user_stories/<epic-slug>.md` (legacy: repo-root `docs/stories/` until migration finishes); the "Stories served" pointer above is the bridge.
- **Open questions** → the artifact they belong to: task flags → tasks `## Carried Flags`; design assumptions → the ADR; requirement questions → the PRD.
- **T1–T6 ledger** → `<slug>/design/phase-b-entry.md` (architect-owned Phase-B artifact).

## When to Update

- After each task closes — advance the **Active pointer + phase** (do NOT append a completed list; the tasks-file tick is the record).
- When a phase changes or a gate is reached.
- When switching away (via `/feature-switch`) and at session end.

## Format

A short note, not a document. The `manager` reads it to resume context and drive the dashboard;
%-done comes from the tasks-file ticks, not from here.
