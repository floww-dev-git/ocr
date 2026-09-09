---
name: fix-sentry-issue
description: Debug and fix a bug reported in Sentry with proper test coverage. Use when the user says "fix Sentry issue", "debug this error", "fix this bug from Sentry", "production error", or shares a Sentry URL or stack trace that needs root-cause analysis and a fix.
argument-hint: "[Sentry issue URL or error description]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Write, Edit, Bash
---

# Fix Sentry Issue

Fix: $ARGUMENTS

Follow the Bug Fix flow from the SDLC. Standards from `@.claude/rules/clean-code.md`, `@.claude/rules/exception-handling.md`, and `@.claude/rules/testing.md` apply.

## Workflow

1. **Reproduce** — get the exact error, stack trace, and input that triggers it
2. **Root cause** — trace the execution path, identify WHY it fails (not just where)
3. **Discuss** — present findings and proposed fix to user
4. **Write failing test** — a test that reproduces the bug (should FAIL before fix)
5. **Fix** — apply the minimal fix, root cause not symptom
6. **Verify** — failing test now passes, all existing tests still pass
7. **Integrate** — run full app test suite, check for pattern bugs elsewhere
8. **Report** — summarize what was wrong, why, and how it was fixed
