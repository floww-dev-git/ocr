---
name: write-feature-kt
description: "Write a feature-kt-document — a short, standardized Knowledge-Transfer doc for the business team covering problem, solution, flow diagram, config changes, breaking changes, and pending debt. Reads the relevant ADRs, user stories, and code first, then writes the doc. Use when the user says 'write feature KT', 'create KT doc', 'feature knowledge transfer document', 'KT document for this feature', 'document this feature for the business team', or 'write the KT'."
argument-hint: "[feature name, branch, ADR ref, or 'this branch']"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Bash
---

# Write Feature KT Document

Write a feature-kt-document for: $ARGUMENTS

> **Audience: the business / ops team — not engineers.** This document is read by the business and operations people who run the product, not by the developers who built it. Write every section for a non-technical reader: plain language, business outcomes, and only the config values they must act on. If a business reader cannot act on a sentence or follow it without reading code, cut it or rewrite it.

## Why this exists

We ship features daily and hand KT to the business team verbally. Cases, flows, config changes, and breaking changes get diluted in people-to-people transfer. This skill produces ONE standardized doc per feature so nothing important is lost in the retelling.

The reader is a business/ops person, not the author. They must finish the doc with a clear mental model and zero open "wait, what about…" gaps — without it feeling like a wall of text.

## The non-negotiable rule

**Each section is max 50 lines** — except the Solution Flow Diagram, which has no limit. If a section runs over, **trim it**, do not ship it long. Be frank. Close sentences with clear, concise words. No filler, no marketing tone, no hedging. Short doc, high signal.

## Step 1 — Determine the feature scope

Do NOT guess from memory. Establish what the feature actually is from evidence:

1. Run `git branch --show-current` and `git log --oneline -15` to read the branch name and recent commits.
2. Run `git diff --name-only <base>...HEAD` (base is usually `dev`) to see changed files, OR if the feature is already merged, use the ADR/user-story the user names.
3. Map changed files to the **owning app** (the Django app that holds the business logic).
4. If scope is ambiguous (multiple features on the branch, unclear owning app), state your read of the scope and **confirm with the user before writing**. One question, not a round-trip series.

## Step 2 — Read the source artifacts (mandatory)

Write from the artifacts, never from assumption. Read all that exist:

- **ADRs** — `<owning_app>/docs/adrs/` (decisions, trade-offs, invariants, what was deferred).
- **User stories** — the epic story file(s) at `<owning_app>/docs/user_stories/<epic-slug>.md` (actors, acceptance criteria, edge cases). The feature's `feature-context.md` "Stories served" line names which epic files + US-ids apply.
- **The code** — interactors, storages, models, jobs, configio modules, GraphQL ops, adapters, constants. This is where the real flow, the real config surface, and the real breaking changes live.
- The owning app's `CLAUDE.md` — load-bearing invariants are often already written there.

If an ADR explicitly lists "Deferred" / "not in vN" items, that is your Section 7 (Tech Debt) — copy it faithfully. Deliberate config decisions and trade-offs the ADR records belong in Section 6 (Config Checkpoints / Decisions Taken).

## Step 3 — Write the 7 sections

Use the template in `references/feature-kt-template.md`. The sections, in order, are fixed:

1. **Problem / Usecase** — the real-world need, from the business/user point of view. Not "we added an interactor" — "PMU could not bulk-load LTPs, so onboarding 500 architects meant 500 manual registrations."
2. **Solution** — what we built, in plain language. What can the user/system now do that they could not before.
3. **Solution Flow Diagram** — see Step 4. **Only section exempt from the 50-line limit.**
4. **Configuration Changes Required** — every config change with a **sample format** (CSV sample, data-loading action name, feature-toggle key, pipeline id, etc.) and a one-line **explanation for each**. If there are none, say "None." plainly.
5. **Breaking Changes** — split into **Config breaking** and **Tech/Code breaking**. Cover both even if one is empty (write "None."). A breaking change is anything that makes an existing config, CSV, API contract, or integration stop working as before.
6. **Config Checkpoints / Decisions Taken** — the deliberate configuration decisions, defaults, and guardrails the team locked in for this feature, and why. This is the "what was decided, and what the business should know about it" record — distinct from Section 4, which is the config an operator must set up. E.g. "feature is dark by default until the toggle is enabled per account"; "account scope is derived from catalog → pipeline, not a direct account field". Decisions actually taken, not pending work.
7. **Tech Debt** — what is knowingly deferred, half-done, or owed (technical or config). Frank. "Expiry flipper job not built — licences go EXPIRED lazily on read, not on schedule."

## Step 4 — The Solution Flow Diagram

Default format is **Mermaid** (embedded ```mermaid code blocks) — it renders inline on GitHub and most viewers, and stays version-controlled with the doc.

**The audience is the business/ops team, not engineers. Keep the diagram low on technical detail.** Use plain-language actors and steps (Citizen, Architect, Officer, System, the records/store being read or written). Do NOT name internal services, classes, interactors, adapters, rule-set ids, or field-reference ids in the diagram — that is implementation tourism a business reader cannot use. Describe what happens in business terms ("System recognises the licence", not "rules_engine.evaluate_rule_sets with purpose AUTO_FILL_LTP_LICENCE_NUMBER"). Internal mechanics, if worth recording, belong in Section 2 or 4 prose — never the picture.

Choose ONE of:
- **Separate actor diagrams** (e.g. citizen flow, architect flow, officer flow) — when actors have genuinely different journeys that get confusing if merged.
- **One merged flow diagram** — when actors share a single backbone flow. Usually cleaner; prefer it unless merging hurts clarity.

**Be careful: the SYSTEM is very often an actor.** Background jobs, schedulers, event handlers, lazy-on-read state transitions, validation gates, get-or-create side effects — these are system actions, not user actions. Do not draw a flow that silently skips them. If a stage "just happens" without a human, the system did it — show the system.

Pick `sequenceDiagram` for actor↔system message exchanges, or `flowchart` for decision/branch-heavy flows. Keep node labels short.

## Step 5 — Enforce length and tone before saving

- Count lines per section. Any non-diagram section over 50 lines → cut it down. Merge bullets, drop the obvious, keep the load-bearing.
- Read it once as the business reader. If a sentence hedges or pads, rewrite it shorter.
- Every config change has a sample + explanation. Every breaking-change subsection (config, tech) is present.

## Step 6 — Save

Save to `<owning_app>/docs/feature_kt/<feature-name>.md` — feature docs live under the owning app, alongside `docs/adrs/`. Use a kebab-case `<feature-name>` derived from the feature/branch. Create `docs/feature_kt/` if it does not exist.

Present the path and a one-line summary when done.

## Rules

- **Read before writing** — ADRs, user stories, and code first. A KT doc disconnected from the real code misinforms the business team, which is worse than no doc.
- **Max 50 lines per section** (diagram exempt). Trim, never pad.
- **Both breaking-change kinds** — config AND tech. Never collapse them; never silently drop one.
- **System-as-actor** — if the system acts in the flow, it appears in the diagram.
- **Frank and concise** — plain words, closed sentences, business-reader perspective. No implementation tourism.
- **Decisions vs debt** — Section 6 records config decisions actually taken (done, deliberate); Section 7 records what is still owed. Don't mix them.
- **Faithful debt** — Section 7 reflects what is actually deferred per the ADR/code, not a wish list.
