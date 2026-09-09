# Consent Granularity

## The Principle

When the user approves a plan, the agent executes the plan end-to-end and pauses only at the canonical approval gates. Sub-decisions inside an approved plan are resolved by the agent choosing a sensible default, announcing it, and giving the user an override opportunity — not by a round-trip question. This rule applies to EVERY agent and the main session.

## Canonical Approval Gates (the ONLY pause points)

Defined in `agent-delegation.md` (Pipeline Continuation):

1. After requirements (PRD + user stories presented as one deliverable)
2. After ADR
3. After implementation plan
4. Before push (per-task local commits are automatic; the one gate reviews the series and pushes)

No other point in the pipeline is a gate. If a step is already on an approved plan, it proceeds automatically.

## Announce-and-Execute Pattern

When a sub-decision arises inside an approved plan, the pattern is:

> **Action statement + default chosen + one-line rationale + override invitation.**

All in one message. Then execute. If two or more genuine questions must be asked, put them in ONE message, not serially.

### Right

> "Committing the 4 rewritten CLAUDE.md files. Excluding `claude-md-task-plan.md` (local tracker, not product code). Proceeding to the next rewrite on the plan (project root CLAUDE.md). Reply to override either."

> "Regenerating GraphQL schemas before commit because `sales_crm_graphql/mutations/` changed. Running both schema_gen commands. Will show the diff before staging."

### Wrong (serial round-trips)

> "Should I also commit the tracker file?" [wait] "Should I proceed with the next rewrite?" [wait] "Should I regenerate schemas now?" [wait]

## Defaults to Apply Without Asking

These are NEVER questions — the agent picks the default and announces it:

| Sub-decision | Default | Announce as |
|---|---|---|
| Include local tracker/plan file in product commit | Exclude | "Excluding `<file>` (local artifact, not product code)" |
| Proceed to next item on an approved plan | Proceed | "Moving to next item: `<item>`" |
| Include unrelated changes accidentally staged | Exclude from this commit | "Excluding `<file>` — unrelated to this task" |
| Schema regeneration when schema files changed | Regenerate | "Regenerating schemas because `<path>` changed" |
| Test fixture update when a test breaks on a field rename | Update fixture | "Updating the fixture to match the renamed field" |
| Formatting / import order when committing | Apply project style | "Applying ruff format before staging" |
| Splitting a large file per the 500-line rule | Split | "Splitting into `<a>.py` and `<b>.py` to stay under the file limit" |
| Continue vs halt after a recoverable non-blocking warning | Continue | "Warning `<msg>` noted — continuing, will revisit if it blocks" |
| Concept lock after the user picks a shape | Lock + draft the PRD | "Locking concept `<X>` — drafting the PRD" |

## When to Actually Ask

Reserve questions for sub-decisions with **materially different business consequences** not already implied by the approved plan: data-migration confirmations against UAT, two valid designs with different perf trade-offs, ambiguous user-story semantics. Everything else gets the announce-and-execute treatment.

## Pre-Gate vs Post-Gate — Do Not Conflate

This rule governs **post-gate** behaviour only. Before a gate is passed, the agent is building the artifact the gate will approve (PRD, user stories, ADR, plan). Scope interpretations formed during that building phase are NOT announce-and-execute defaults — they are clarifying questions disguised as conclusions, and they must be resolved WITH THE USER before the gate closes.

### The trap

When the user gives a terse request ("clone these TNC models, TNC is stage-transition-only for now"), the agent often forms interpretations to fill gaps: which models are in scope, which attributes narrow the scope, what is explicitly excluded. These are **pre-gate interpretations**. They look like defaults ("I'll exclude the audit log table — obviously not cloneable"), but they are actually the SUBSTANCE of the user-story / plan that gate 1 exists to approve. Treating them as announce-and-execute defaults and embedding them in a delegation to the next agent collapses gate 1 without the user ever seeing it.

### The rule

If an agent (especially the manager) is at or before a gate and forms an interpretation that:
- Narrows user-stated scope (excludes items the user did not explicitly exclude), OR
- Expands user-stated scope (includes items the user did not explicitly include), OR
- Resolves an ambiguity the user did not resolve

...that interpretation is a **clarifying question**, not a default. The agent must surface it to the user and get confirmation BEFORE delegating or before treating the plan as approved.

### Right (pre-gate)

> "Your request says 'TNC exists for stage transition only for now'. Before I hand off, confirming scope: (1) cloneable set = `TncTermsSet` + `TncTermsSetVersion` + `TncTerm` (excluding `TncActionLog` — looks like an audit log, shouldn't follow the clone). (2) Filter on `entity_type = STAGE_TRANSITION` only. Confirm or correct before I delegate to the developer."

### Test

Before delegating to the next agent, ask: "Am I embedding any assumption the user did not explicitly state?" If yes, surface it as a question first. The delegation message should contain only user-confirmed facts plus implementation guidance — never unconfirmed scope interpretations.
