# The Living Review Page — one HTML surface per feature

A gate is only as strong as the reviewer's comprehension at it. The markdown artifacts (PRD,
`flows.md`, and the epic story files at `<owning_app>/docs/user_stories/<epic-slug>.md`) are CANONICAL — agents
parse them downstream; the review page is a
RENDERING for the human's eyes, regenerated from the markdown every pass and never hand-edited
into divergence. Two jobs: (1) make each gate's approval an informed one, (2) make iteration
rounds diffable at a glance.

## Home & lifetime

- One page per feature: `review-<slug>.html` at the **worktree root** (transport artifact,
  like `feature-context.md` — never committed to app docs; the markdown is the record).
- Born at the PRD draft; **alive until the feature is delivered** (user-set); retired with the
  worktree. It is NOT documentation — the markdown artifacts outlive it.
- Single-writer discipline applies (`agent-teams-pipeline.md`): the manager owns the page
  during Phase A; regenerate from disk, never from conversation memory.

## Growth per pass (progressive, never rebuilt from scratch)

| Pass | The page gains |
|---|---|
| PRD draft → ◆1a | Problem · JTBD · value proposition · scope (IN/OUT side-by-side) · actors · candidate modules — each section collapsible, takeaway-first |
| Flows → ✓ | The journeys as ACTUAL diagrams (SVG/HTML flow charts, one per actor journey, failure paths as red edges, interruption edges dashed) — never prose renderings of shape |
| Stories → ◆1b | Story cards NESTED under the flow step each serves — the reviewer sees derivation, not a flat list |
| Phase B+ | Thin B-passes written by the ARCHITECT (artifact owner writes the pass): grounding-digest summary, then decision-card digest + links out to the Module Blueprint and ADR — link, never inline; the blueprint stays its own surface |
| Gate 2 | The **ADR digest** (see `/create-adr` Gate-2 Digest): decision cards new-at-ADR spotlit, carried cards collapsed · Forces → Decisions map (unanswered forces flagged) · extension cost · ⚠ risky-ASSUMES — full ADR + blueprint linked, never inlined |
| Gate 3 | The **breakdown digest** (see `/task-breakdown` Interaction): map ✓'d · decision cards · slice tables · ⚠ attention flags · not-doing list — tasks files linked, never inlined. The human approves decisions; the file is the machine's copy |

## Structure: ONE file, hash-routed sub-pages

The page is a single HTML file with internal sub-pages (hash router, e.g. `#/decisions`) —
one URL per feature, no sibling files to hunt for:

```
review-<slug>.html
├ #/overview    the status rail — phases, gates passed/pending, what's awaiting the user NOW
├ #/prd         the PRD rendered (draft-diff highlighting on iteration)
├ #/flows       the journeys as diagrams
├ #/stories     story cards nested under their flow steps
├ #/design      Gate-2 pass: ADR digest (cards spotlit, F#→Dn map, ⚠ flags)
├ #/decisions   the DECISION LOG — every card across all phases (concept lock →
│               blueprint L2 → ADR → breakdown ## Decisions footer), each:
│               CHOSEN · OVER · BECAUSE · phase · link to its canonical source
└ #/breakdown   Gate-3 pass: map ✓ · slice tables · ⚠ flags · not-doing
```

The page lives in the feature folder — `<app>/docs/features/<slug>/review.html` — alongside the
artifacts it renders. The Module Blueprint stays a SEPARATE file only because its lifetime
differs (committed under `<app>/docs/design/`, it's MODULE documentation that outlives the
feature; the review page retires at delivery) — the nav links it like a sub-page.

UX bar (defer to `frontend-design` for the full standard): persistent sidebar/tab nav with the
gate-progress state visible on every sub-page · takeaway-first, detail collapsed · nothing
requires scrolling a wall — progressive disclosure over length · the sub-page awaiting user
action is visually marked · change-highlighting on every re-presented pass.

## Non-negotiables

- **UNCONFIRMED items are visually flagged** (badge + named consequence) — the page must make
  honest holes MORE visible than confident filler, never less.
- **Change highlighting on iteration** — a re-presented pass marks what changed since the last
  look (added / removed / reworded), so round 2 costs the reviewer only the delta.
- **Aesthetic bar** — defer to the `frontend-design` skill: intentional palette, progressive
  disclosure (collapsed detail, popovers), readable without scrolling walls. The
  requirement-side sibling of `/module-blueprint`'s design report.
- **No second truth** — every fact on the page traces to a markdown artifact by path; a fact
  that exists only on the page is a bug.
