---
name: write-prd
description: "Write a Product Requirement Document (PRD) for a feature or change request. The PRD is the entry contract to the SDLC pipeline — it feeds the manager agent for user story decomposition. Use when the user says 'write a PRD', 'create a PRD', 'draft requirements', or needs to formalize a feature idea before the SDLC pipeline begins."
argument-hint: "[feature idea, problem description, or rough requirement]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write
---

# Write PRD

Write a PRD for: $ARGUMENTS

The PRD is the **entry contract** to the SDLC pipeline. The manager agent consumes it to produce user stories. Every ambiguity here compounds through architecture, implementation, and review. Be explicit, be precise, be complete.

## Fed By (the input contract)

A PRD is a TRANSFORMATION, never a creation. Its only legitimate inputs:
1. **Raw human intent** (mandatory — no intent, no PRD)
2. **Source documents** when they exist (GR/circular, tender sheet, client email, incident report)
3. **Codebase reality** (you dig — Step 1)
4. **Clarifying Q&A** (answers extracted from the human — Step 2)

**The NO-INVENTION rule:** thin input produces questions back at the human, NEVER a padded document. You contribute structure, gap-detection, and codebase grounding — never requirements. A fabricated section reads downstream as human-confirmed truth and silently suppresses the clarifying questions Gate 1 exists to force. The sections with no second copy anywhere in the pipeline — Out of Scope, Constraints & Dependencies, Domain Terminology — are the most dangerous to fabricate (a lie there is uncontradictable downstream) and carry the strictest confirmation bar.

**Consumers:** manager (primary — decomposes into user stories via /intake-requirement) · architect (read-only secondary — reads Out-of-Scope, Constraints, Terminology, Error Scenarios; stories don't carry them).

## Step 1: Understand the Problem

1. If a file path or document is given, read it
2. If inline description, analyze it
3. **Search the codebase** — identify which apps, models, and interactors are already involved (Grep/Glob/Read). The PRD must be grounded in what exists
4. **Present your understanding** — summarize the problem back to the user in 2-3 sentences
5. Do NOT proceed without confirmation that you understood correctly

## Step 2: Gather Requirements (Interactive)

Ask clarifying questions in a single numbered batch. Cover ALL of these:

**Problem & Motivation:**
- What pain exists today? Who feels it?
- Why now? What triggered this need?

**Desired Outcome:**
- What can the user do after this ships that they cannot do today?
- What does success look like from the user's perspective?

**Scope:**
- What is explicitly IN scope?
- What is explicitly OUT of scope? (this is more important than the IN list)
- Are there related features that should NOT be touched?

**Domain:**
- What business terms are involved? Do any terms have specific meaning in this codebase that differs from common usage?
- Are there business formulas or calculations? (never assume — ask explicitly)

**Constraints:**
- Which existing systems does this touch?
- Performance requirements? Data volume expectations?
- Compliance, security, or permission requirements?
- External integrations involved?

**Error Scenarios:**
- What should happen when things go wrong?
- What are the known edge cases?

**Data:**
- Can you provide concrete input/output examples?
- Before/after scenarios?

Do NOT ask questions the code can answer — search first, ask only what requires business context.

## Step 3: Draft the PRD

Generate the PRD using this exact structure:

```markdown
# PRD: [Feature Name]

**Date:** [today's date]
**Author:** [user]
**Status:** Draft
**Owning App:** [Django app that owns this feature]

## Problem Statement

[1-2 paragraphs: what pain exists, who feels it, why it matters now]

## Job To Be Done

[The job the user "hires" this feature for, in their words — situation → motivation → expected outcome. One JTBD per PRD; competing jobs mean competing concepts that should have been separated at ideation.]

## Value Proposition

[Why this beats the status quo for that job — what the user stops suffering or starts gaining. Falsifiable: if you can't say what gets measurably better, the feature is decoration.]

## Desired Outcome

[What the user can do after this ships — observable behavior, not implementation]

## Chosen Concept

[The picked shape, 2-3 lines: JTBD, actors, what it does — bound at concept lock]

## Rejected Shapes

- [shape] — [one-line why not]

## Assumptions

[What the chosen shape presumes true — each becomes a check the impact audit verifies]

## Actors & Roles

| Actor | Role in this feature | Permissions context |
|---|---|---|
| [actor] | [what they do] | [role/permission notes] |

## Key Modules (candidates)

[The modules this likely touches, from the validated candidate list — honestly labeled as
CANDIDATES from the capability layer, never witnessed claims. Phase B verifies with design
authority; do not read code to "confirm" these here.]

## Scope

### In Scope
- [bullet list of what this feature covers]

### Out of Scope
- [bullet list of what this feature explicitly does NOT cover]

## Domain Terminology

| Term | Definition (as used in this codebase) |
|---|---|
| [term] | [precise definition] |

## Acceptance Criteria

[Feature-level, outcome-oriented. NOT Given/When/Then — that is user story level.]

- AC1: [outcome statement]
- AC2: [outcome statement]
- AC3: [outcome statement]

## Error Scenarios

| Scenario | Expected Behavior |
|---|---|
| [what goes wrong] | [what the system should do] |

## Constraints & Dependencies

> Anything the capability layer and the human can't answer stays `UNCONFIRMED` with a named consequence — an honest hole beats confident filler. Deep verification happens in Phase B (design), not here; never read code to fill this section.

- **Existing systems affected:** [list]
- **Performance:** [requirements if any]
- **Security/Permissions:** [requirements if any]
- **External integrations:** [list if any]
- **Data volume:** [expected scale]

## Data Examples

### Example 1: [scenario name]
**Input:**
[concrete data]

**Expected Output:**
[concrete data]

## Open Questions

- [anything unresolved that needs product/business input]
```

## Step 4: Validate Completeness

Before presenting, verify the PRD against this checklist. **Semantics: a section passes if it is human-confirmed OR explicitly marked `UNCONFIRMED — needs input` (listed in Open Questions). NEVER fill a section to satisfy a minimum — an honest UNCONFIRMED beats confident filler.**

- [ ] Problem statement answers "what pain" and "who feels it"
- [ ] Desired outcome is user-observable, not implementation detail
- [ ] OUT of scope list exists and is non-empty
- [ ] Every domain term used in ACs is defined in the terminology table
- [ ] Acceptance criteria are feature-level outcomes (not Given/When/Then)
- [ ] At least 2 error scenarios are documented
- [ ] At least 1 concrete data example exists
- [ ] No implementation details leaked in (no "add a model", "create a mutation", etc.)
- [ ] Consistent terminology throughout — same concept uses same term everywhere
- [ ] Actors & Roles section present — every story-able actor enumerated
- [ ] JTBD present — one job, in the user's words; Value Proposition falsifiable
- [ ] Key Modules present — labeled as candidates, no code-verified claims
- [ ] Chosen Concept present with ≥1 rejected shape (class-1 features) — or explicitly marked single-shaped
- [ ] NO User Flows in the PRD — flows are a separate artifact, planned after Gate 1a (`/write-user-flows`)

If any item fails, fix it before presenting.

## Step 5: Present & Iterate

1. Present the full PRD to the user
2. Explicitly call out the Open Questions section
3. Wait for user feedback — iterate until approved
4. Flag any areas where you suspect missing context

## Step 6: Save

Save at **draft time** — not approval time — to `<owning_app>/docs/features/<feature-slug>/prd.md`
with `Status: Draft`. The living review page renders the draft BY PATH, and iteration rounds
diff against it; a PRD that exists only in conversation cannot be reviewed. Gate 1a approval
flips `Status: Draft → Final` in place — same file, no copy.

If the feature folder does not exist, create it (the slug matches the `feature/<slug>` branch;
all of this feature's artifacts co-locate there).

## Rules

- **No implementation details** — the PRD defines WHAT and WHY, never HOW. "Use DynamoDB" or "add a GraphQL mutation" does not belong here
- **No Given/When/Then** — that is user story format. PRD acceptance criteria are outcome statements. The manager agent decomposes these into Given/When/Then during user story creation
- **Consistent terminology** — if you call something "order" once, never call it "transaction" later. Agents are literal interpreters
- **Be explicit about exclusions** — anything mentioned casually becomes a user story. If it is not in scope, say so in the OUT list
- **Ground in the codebase** — reference existing entities, apps, and patterns. A PRD disconnected from reality produces user stories that cannot be implemented
- **Business formulas must be stated** — per clean-code rules, developers must never assume formulas. If the feature involves calculations, the PRD must spell them out
- **No invention** — every substantive statement traces to the human's words, a source document, or the codebase. Anything else is a question, not content
- **Provenance discipline** — sole-witness sections (Out of Scope, Constraints & Dependencies, Domain Terminology) require explicit human confirmation; mark anything else `UNCONFIRMED` rather than guessing
