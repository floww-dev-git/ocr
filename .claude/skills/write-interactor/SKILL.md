---
name: write-interactor
description: Design and implement an interactor following clean architecture patterns. Use when the user says "write an interactor", "implement business logic", "create a use case", or needs a new interactor class built with DTOs, storage interfaces, and tests.
argument-hint: "[use case or ADR reference]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Write Interactor

Implement interactor for: $ARGUMENTS

Follow @.claude/rules/interactors.md and @.claude/rules/clean-architecture.md

## Workflow

1. If unclear on the use case, ask for clarification
2. Load app context — skim models, storages, interactors, app interfaces, adapters
3. Ask key design questions not covered in the ADR
4. Propose an interactor design (**don't code yet**)
5. Self-review:
   - All cases covered?
   - Follows all guidelines?
   - Can reuse existing interactors, mixins, validations?
6. Ask for feedback → integrate → repeat until approved
7. Write the code
8. Self-review against @.claude/rules/clean-code.md
9. Ask for review → integrate → repeat until approved
10. Ask user to proceed to test cases
11. List test scenarios with data states
12. Implement each test case one at a time, taking feedback per test
