# CLAUDE.md Content Guide

## Litmus Test

For every line: **"Would removing this cause Claude to make a wrong decision?"** If no, delete it.

## Required Sections

| Section | What goes in it |
|---|---|
| **Scope boundary** | One line: "Handles X. Does NOT handle Y (that's `other_app`)." |
| **Dependencies** | Internal consumed (via adapters), internal exposed (via app_interfaces), external services |
| **Critical definitions** | Domain terms with specific meaning in this codebase that differ from common usage |
| **Core entities** | Table: entity name + role. NOT field lists. |
| **Entity relationships** | Condensed tree or diagram showing how entities connect |
| **State machines** | States, valid transitions, disallowed transitions, side effects |
| **Business rules** | Non-obvious invariants, validation chains, constraints from contracts/regulations |

## Optional Sections (include only if they prevent mistakes)

| Section | When to include |
|---|---|
| **Revenue/data protection** | If the app handles money or sensitive data |
| **Gotchas** | Active pitfalls with severity that cause real bugs |
| **Known issues** | Open bugs with severity and workarounds |
| **Test layout** | If non-standard test structure |

## What NOT to Include

| Exclude | Why | Where it belongs |
|---|---|---|
| Code examples | Goes stale, derivable from code | Nowhere (read the code) |
| Coding conventions | Already enforced | `.claude/rules/` |
| Django/Python standards | Claude already knows | `.claude/rules/` |
| Setup/install instructions | Not app-specific | Root `CLAUDE.md` |
| Testing instructions | Not app-specific | Root `CLAUDE.md` or rules |
| Architecture layer explanations | Not app-specific | `.claude/rules/clean-architecture.md` |
| File-by-file descriptions | Derivable from code | Nowhere |
| Feature descriptions / marketing | Zero decision value | Nowhere |
| Frequently changing values | Goes stale | Constants files in code |

## Anti-Patterns (discovered in this project)

1. **Fabricated code** — invented classes/methods that don't exist in the codebase. Actively harmful — causes hallucination-on-hallucination.
2. **Directory listings** — restating folder names as sentences ("deals: CRUD for deals"). An `ls` tells you the same thing.
3. **Marketing copy** — "sophisticated", "advanced", "enterprise-grade", "comprehensive". Zero decision value.
4. **Pattern tutorials** — explaining interactor/DTO/storage patterns already in rules. Duplicates and drifts.
5. **Echoing the obvious** — describing what an agent would learn in 30 seconds of reading the code.
6. **Bloated files** — 300+ lines consume context budget for no benefit. Agents skim or ignore them.

## Size Targets

| Level | Target | Hard limit |
|---|---|---|
| App-level CLAUDE.md | 80 lines | 250 lines |
| Sub-folder CLAUDE.md | 40 lines | 100 lines |
| Root project CLAUDE.md | 80 lines | 150 lines |

## Sub-Folder CLAUDE.md Strategy

Most packages do NOT need their own CLAUDE.md. Only create one when:
- The package has complex state machines or business rules that don't fit in the app-level file
- The package has non-obvious conventions that differ from the app norm
- An agent has repeatedly made mistakes in this package due to missing context

## Template

```markdown
# {App Name}

{One sentence: what this app does. What it does NOT do (and which app does).}

## Dependencies
- **Consumed:** list of apps/services this app uses via adapters
- **Exposed:** list of app_interfaces this app provides
- **External:** third-party services

## Critical Definitions
- **{Term}** — what it means in THIS codebase (if different from common usage)

## Core Entities

| Entity | Role |
|---|---|
| `EntityName` | One-line role description |

## Entity Relationships
{Condensed tree or diagram}

## State Machines

### {Entity with lifecycle}
{States, transitions, disallowed transitions, side effects}

## Business Rules
- {Non-obvious rule with consequence of violating it}

## Gotchas

| Issue | Impact |
|---|---|
| {Pitfall} | {What breaks} |
```

## Gold Standard Reference

`payments_engine/CLAUDE.md` — 178 lines, every section passes the litmus test.
