# Agent Delegation

## How routing works

Every agent's trigger phrases and domain live in its own `description` (`.claude/agents/<agent>.md`). The harness injects that roster as the router: match the user's message to an agent and delegate via the Agent tool — never handle a delegable request in the main session. To change routing, sharpen a description; don't grow a table here. This file holds only the judgments a single description can't express:

- **Scope-guard** — delegate to the named agent ONLY if the request is in its domain. Outside its scope → re-route and tell the user. Composite request → delegate to the named agent to decompose.
- **`task-coordinator` has no user-facing address** — the `manager` spawns it to drive one slice's inner dev loop; the user never invokes it.

## When routing is ambiguous

- **Explicit address wins** — `@name` / "hey <agent>" beats a competing trigger-phrase match.
- **`.claude/` path → `dhruva`** — any create/modify of a `.claude/` config file goes to dhruva, even with no config trigger word (hard override; `config-delegation.md`).
- **Still unclear → ask the user.**

## Pre-Implementation Gate

New features route to `manager` first, even if the user says "implement". The manager drives `/intake-requirement`, which triages {new concept · update · bug fix · refactor} and picks the exit ramp per class.

**Skip when:** user says "skip analysis" / "just implement it", a complete plan is provided (user stories + acceptance criteria + task breakdown), or an approved ADR is referenced.

## Design Correction Routing

When the developer finds a planning artifact wrong mid-implementation, the main session coordinates the fix (it does NOT hand everything to one agent). Route: PRD / user stories → `manager`; ADR / task list → `architect`; both → `manager` first, then `architect`. User approves the corrected docs before the developer resumes. Full protocol: `references/dev-loop-corrections.md`.

## Don't delegate

- Simple questions, file reads, single-file lookups — use Read/Grep/Glob directly.
- Git operations — main session, or the `developer`.
- Any low-judgment work — agents add context overhead; reserve them for domain judgment or multi-step reasoning.

## Pointers

- **Pipeline** — agents auto-chain, pausing only at the 4 approval gates (enumerated in `dev-loop.md`). **Scout is NOT in the auto-chain**: invoking `@scout` pauses the pipeline for its run but inserts no gate. Full auto-chain table + team composition: `references/agent-teams-pipeline.md`.
- **Delegation payload** — pass persona, memory, and prior pipeline context per the clarity-cascade template; background agents follow single-writer discipline (re-read shared files before editing, report to files). Both in `references/agent-teams-pipeline.md`. Invoke Dhruva after an agent completes if corrections or learnings emerged.
