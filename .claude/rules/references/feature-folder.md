# Feature Folder — canonical layout & naming

The single home of the feature-folder structure. Every skill that saves a feature artifact
follows this; the writing skill's save step names its exact subpath. One folder = one feature,
under the owning app: `<owning_app>/docs/features/<feature-slug>/` (slug = the `feature/<slug>`
branch name).

## The tree

```
<owning_app>/docs/features/<slug>/
├─ feature-context.md            tracked session state (manager-owned; fixed name)
├─ prd.md                        Phase A — fixed names, no prefixes
├─ flows.md
├─ design/                       Phase B working artifacts (multiply per slice)
│   ├─ phase-b-entry.md          the architect's T1–T6 escalation ledger
│   ├─ parity-study.md           class 4: the Step-0 inventory
│   ├─ slice-plan.md             class 4: the approved slice sequence
│   ├─ s<N>-db-design.md         per-slice schema spec
│   ├─ s<N>-walkthrough.html     per-slice design walkthrough / blueprint render
│   └─ s<N>-gate2-qa.md          gate Q&A records
├─ adrs/
│   └─ ADR-NNN-<short-name>.md   numbered PER FEATURE, starting 001
├─ tasks/
│   └─ tasks-ADR-NNN-<name>[--module].yaml  (validated by check-tasks-yaml.py on tasks-ADR-*.yaml)
├─ reviews/
│   └─ <scope>-review.md         scope = task id (task-2.3) or `final`; re-reviews append
├─ test-report.md                tester: AC-traceability matrix + coverage (fixed name)
└─ review.html                   living review page (retires at delivery; fixed name)
```

Module blueprints are the ONE exception — module documentation with module lifetime, they stay
at `<app>/docs/design/` (they outlive the feature).

## Stories live in the app, not the feature folder

User stories are NOT in the feature folder. They live with the app that owns the capability, one
file per epic: `<owning_app>/docs/user_stories/<epic-slug>.md`.

WHY they leave the feature folder: an epic (a product capability) outlives any single feature —
several features add stories to the same epic over time — so a branch-scoped folder would split
one capability across many folders.

WHY they stay in the app: every other doc lives with the owning app (`dev-loop.md`). Stories are
not an exception. Same owning-app choice as the feature folder; a multi-app capability lives in
the primary owning app.

The feature links to its stories through `feature-context.md` (which epic file(s) + US-ids it
serves) and the ADR header. Full rules — epic-slug reuse, US-id uniqueness, slug-qualified flow
citations, single-writer discipline — live in `.claude/skills/write-user-stories/SKILL.md`.

Repo-root `docs/stories/<epic-slug>.md` is the LEGACY home. Files still there are waiting to be
moved; read from it as a fallback, write new stories only to the app path.

## Naming rules

1. **No feature prefixes inside the folder** — the folder IS the feature; `parity-study.md`,
   never `REF-001-parity-study.md`. A prefix that repeats the folder name is noise on every ls.
2. **Slice-scoped artifacts carry a lowercase slice prefix** — `s1-db-design.md`,
   `s3-walkthrough.html`. Feature-scoped artifacts carry none.
3. **Canonical artifacts use FIXED names** — `feature-context.md`, `prd.md`, `flows.md`,
   `test-report.md`, `review.html` — so every tool and reader greps one string
   across all features. (User STORIES are the exception — they live OUTSIDE the folder; see below.)
4. **Kebab-case, lowercase** everywhere except the established `ADR-NNN-` and `tasks-` prefixes.
5. **Families that multiply get a subfolder** (design/, adrs/, tasks/, reviews/); singletons
   stay top-level. A subfolder with one file forever is over-organization — but ADRs, tasks,
   and reviews always multiply.
6. **Nothing else at top level** — a new artifact kind either matches an existing family or
   gets flagged to dhruva before inventing a new location.
