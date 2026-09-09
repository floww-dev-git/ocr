---
name: plan-feature
description: Full planning flow for a new feature — from PRD analysis through user stories, architecture design, ADR, to task list generation. Use when starting a new feature.
argument-hint: "[feature description or PRD path]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Bash
---

# Plan Feature

Plan: $ARGUMENTS

## Process

### Phase 1: Understand Requirements

Run `/intake-requirement $ARGUMENTS` — the Phase A driver takes the ask through triage, concept, PRD, and stories (Gates 1a/1b). Do not proceed to Phase 2 until stories are approved.

### Phase 2: Architecture Design

1. **Load app context** — read each relevant app's `CLAUDE.md`, then its layers in order (models → storage interfaces → interactors → app_interfaces → adapters)
2. **Map the data flow:**
   - Which apps are involved (new or existing)?
   - Models → Storage interfaces → Interactors → Presenters → GraphQL
   - Inter-app dependencies → adapters needed?
3. **Follow** `@.claude/rules/clean-architecture.md`

### Phase 2b: Refactoring Assessment

While reviewing existing code during architecture design:
1. **Identify blocking debt** — code that must be refactored before the feature can be built safely
2. **Identify adjacent debt** — messy code in the same area, cheaper to fix now while context is loaded
3. **Log deferred debt** — known issues outside scope, note in ADR consequences section
4. Refactoring tasks are planned as **separate tasks** — never mixed into feature tasks

### Phase 3: ADR

1. **Create ADR** — `/create-adr $ARGUMENTS`
2. Document: context, decision, alternatives, consequences, implementation plan

**Review gate:** ADR must be reviewed and approved before proceeding.

### Phase 4: Task List

1. **Generate tasks** — `/task-breakdown [ADR path]`
2. Each task must be:
   - **Atomic** — one deliverable
   - **Self-checkable** — concrete validation step
   - **Dependency-ordered** — no reverse dependencies
3. Standard order: models → DTOs → storage interfaces → interactors → presenters → GraphQL → adapters → event handlers

**Review gate:** Task list reviewed for scope and ordering.

### Phase 5: Update Feature Context

Update the feature's `feature-context.md`:
- Set phase to "Tasks"
- Populate pending tasks list
- Link to ADR and task list paths
