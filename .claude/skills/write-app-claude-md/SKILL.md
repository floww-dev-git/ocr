---
name: write-app-claude-md
description: Write or rewrite a Django app's CLAUDE.md using bottom-up code analysis and the content guide. Use when creating new app CLAUDE.md files or rewriting bloated ones.
disable-model-invocation: false
argument-hint: "<app_name> (e.g., sales_crm_core, bps, fee_engine)"
allowed-tools: Read, Glob, Grep, Edit, Write, Agent, Bash
---

# Write App CLAUDE.md

Write or rewrite the CLAUDE.md for Django app: **$ARGUMENTS**

## Process

### Step 1: Analyze (Architect Agent)
Spawn the `software-architect` agent to analyze the app bottom-up:
1. **Models** — entities, relationships, FK/M2M/GenericFK patterns
2. **Constants/Enums** — domain vocabulary, state definitions
3. **Interactors** — state machines, business rules, validation chains, side effects
4. **Exceptions** — implicit constraints encoded as exception classes
5. **App Interfaces** — what this app exposes to others
6. **Adapters** — what external apps/services this app consumes

### Step 2: Draft
Write the CLAUDE.md using the template in `@.claude/skills/write-app-claude-md/references/claude-md-content-guide.md`.

### Step 3: Quality Gate
Review every line against the litmus test: **"Would removing this line cause Claude to make a wrong decision?"** If no, delete it. Check for all 6 anti-patterns listed in the content guide.

### Step 4: Sub-Folder Assessment
Decide if any sub-folders need their own CLAUDE.md. Most don't — only create for packages with genuinely non-obvious domain knowledge that can't fit in the app-level file.

### Step 5: Present for Review
Show the user the file for feedback. Iterate until approved.
