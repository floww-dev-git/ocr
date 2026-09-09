---
name: ai-readiness-check
description: Enforce the AI readiness gate — every new Django app or significant new module must have a CLAUDE.md before a feature is considered complete. Use when the diff introduces a new `apps.py`, a new `INSTALLED_APPS` entry, or a new significant subpackage (interactor subpackage, `jobs/`, `tasks/`, configio module, new `adapters/` integration, new `event_handlers/` subpackage).
---

# AI Readiness Check

## WHY
New apps and modules without CLAUDE.md files cost every future AI session 5-10 minutes of file-reading to reconstruct context that 5 lines would have provided. This gate makes AI discoverability a hard requirement, not an afterthought.

## Triggers

### New Django App
Any of these signals mean a new app was added:
- New `apps.py` file created
- New entry added to `INSTALLED_APPS`
- New top-level directory with `models/`, `interactors/`, or `__init__.py` matching the app pattern

### New Significant Module
A new subpackage within an existing app that introduces non-obvious domain knowledge:
- New interactor subpackage (e.g., `interactors/configio/<new_entity>/`)
- New `jobs/` or `tasks/` module with background processing logic
- New configio module (import/export for a new entity type)
- New `adapters/` integration with an external service
- New `event_handlers/` subpackage

A module is "significant" if the folder name alone does not explain what it does, what state it manages, or what business rules it enforces. Most new files within existing modules do NOT qualify.

## Deliverables

### For a New App (all three required)

1. **App-level `CLAUDE.md`** at the app root
   - Delegate to Dhruva using `/write-app-claude-md` skill
   - Quality standards defined in `config-delegation.md` (Folder CLAUDE.md Convention) apply
   - Size target: 80 lines, hard limit 250

2. **Project-level `CLAUDE.md` updated**
   - New app listed in the "Django Apps" section under the correct category
   - App dependency map in `clean-architecture.md` updated if the app introduces new inter-app dependencies

3. **Feature context file updated**
   - Note which app was created and that AI readiness was completed

4. **Module map regenerated** — `python3 .claude/scripts/generate-module-map.py`
   - The map (`rules/references/module-map.md`) is a generated view of app CLAUDE.mds, consumed by the intake cheap-scan; a new app's card must appear in it, and the script's gap check confirms coverage
   - Also regenerate when an app-level `CLAUDE.md`'s opening capability line changes

### For a New Significant Module

1. **Module-level `CLAUDE.md`** (only if the module has non-obvious domain knowledge)
   - Size target: 40 lines, hard limit 100
   - Skip if the folder name + parent app CLAUDE.md already provides sufficient context

2. **Parent app `CLAUDE.md` updated** to reference the new module's scope and purpose

## Gate Enforcement

This is a hard gate in the dev loop, not a suggestion:
- The feature is **not complete** until AI readiness deliverables are done
- The reviewer agent checks for CLAUDE.md presence when new apps or significant modules appear in the diff
- If a developer skips this, the reviewer flags it as a **High** finding

## Who Does It

- **Developer** flags the trigger during implementation ("I just created a new app/module")
- **Dhruva** writes or updates CLAUDE.md files using `/write-app-claude-md`
- **Reviewer** verifies CLAUDE.md exists and meets quality standards during independent review

## What This Skill Does NOT Cover

- Quality standards for CLAUDE.md content (owned by `config-delegation.md`, Folder CLAUDE.md Convention)
- Proactive maintenance of existing CLAUDE.md files (owned by `config-delegation.md`, Proactive Maintenance Signals)
- When to update CLAUDE.md for changes to existing apps without new modules (owned by `config-delegation.md`)

This skill covers only the **creation gate** for new apps and significant new modules.
