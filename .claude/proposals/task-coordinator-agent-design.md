# Design Brief — `task-coordinator` agent

**Author:** manager · **Date:** 2026-07-06 · **For:** dhruva to encode
**Origin:** REF-001 session retro — problem #1 (the manager, as the longest-lived depth-0
session, accumulates the entire per-task firehose; every turn re-pays for all of it).

## Problem it solves

Subagents return their full report to their parent, and a subagent's context is **discarded
on return**. Today the manager (permanent, depth-0) is the parent of every developer /
reviewer / tester spawn, so all their reports + all idle-ping noise accumulate in the
manager forever. A `task-coordinator` interposes an **ephemeral** context between the manager
and the workers: it absorbs the between-gate dev-loop chatter for a slice, then returns a
few-line summary. The firehose evaporates with the coordinator; the manager's accumulation
rate drops from per-task to per-gate. Structural fix (auto self-cleaning), not disciplinary
(no reliance on remembering to hand off). Also removes idle-notification narration from the
manager/user (item #3): worker pings route to the coordinator.

## Runtime position (the load-bearing constraint)

- Coordinator runs as a **subagent (depth-1), spawned by the manager** — ephemeral by design.
- **Gates MUST stay at depth-0 (manager).** Approval gates only surface to the user from the
  top-level session; a depth-1 coordinator owning a gate would make it invisible. Therefore
  the coordinator **never owns a user-facing gate** — it bubbles UP to the manager at a gate
  boundary or a blocker.

## Division of ownership

| | Manager (depth-0) | Task-coordinator (depth-1, ephemeral) |
|---|---|---|
| Owns | requirements · the ~4 approval GATES · the user interface · cross-slice tracking | everything BETWEEN gates for ONE slice: the dev/review/fix/tick/commit loop |
| Spawns | the coordinator (one per slice) | developers (parallel, app-fenced) · reviewer · tester; routes findings back to devs |
| Accumulates | gate-level Q&A only | the full task firehose + idle pings — then DISCARDS it on return |
| Returns to user | gate presentations | (nothing directly — reports to the manager) |

## Scope unit: per-SLICE, not per-module

The user's framing was "per module," but slices are cross-module (REF-001 S1 touched
workflow_engine + sales_crm_core + iam; its integration closer and push gate span all three).
Pure per-module coordinators leave nobody owning the cross-module seam. **Scope the
coordinator to a slice** (it owns all that slice's module dev-loops), or allow module
sub-coordinators UNDER a slice-level coordinator. The cross-app integration closer and the
push-gate hand-back need a single owner above the modules.

## Manager ↔ coordinator contract

- **Dispatch (manager → coordinator):** "Execute the approved plan for slice Sn (tasks files:
  …). Run the dev loop end-to-end: spawn devs (app-fenced, single-writer), per-task reviews,
  route Crit/High findings back to devs, tick tasks, make per-task local commits. Come back
  ONLY at: (a) the push gate — with the commit series + test report, or (b) a blocker /
  design-correction / T-trip. Enforce file-ownership fencing among workers."
- **Return (coordinator → manager):** a compact summary — tasks done, test counts, review
  verdicts, commit series, carried flags — OR a blocker report. Never the raw worker firehose.
- The manager presents the push gate to the user (depth-0), then instructs the push.

## Complementarity (honest scope)

Solves task-level accumulation (~80% of volume) + idle noise. Does NOT solve gate-level
accumulation across a long multi-slice feature — the manager still accrues gate Q&A. So
fresh-manager handoffs stay complementary, but needed far less often (rate is now per-gate).

## Tools the coordinator needs

Read, Grep, Glob, Bash (git/tests), Edit/Write (tasks-file ticks + a slice-scoped progress
note only — NOT planning docs, NOT .claude config), Agent (to spawn devs/reviewer/tester),
Skill. Mirror the developer/reviewer boundaries; it orchestrates, it does not itself write
production code or author planning artifacts.

## Open questions to VERIFY before finalizing (do not assume)

1. **Nesting depth + notification routing.** Confirm the harness lets a depth-1 coordinator
   spawn depth-2 workers AND that their idle/teammate notifications route to the coordinator
   rather than spamming the depth-0 user. Route this to `claude-code-guide` before committing.
2. ~~**SendMessage across depths** — can the coordinator use SendMessage to resume a teammate's
   interrupted task with context intact (the respawn-vs-resume saving)?~~
   **ANSWERED & REJECTED (2026-07-16).** No — and the question's premise was wrong twice over.
   (a) `SendMessage` is gated by the `tools:` allowlist for spawned subagents; neither the manager
   nor the coordinator is granted it (see the tools list above — it was never in scope).
   (b) "Context intact" is unverified and the docs lean against it: a SendMessage resume "starts
   a new run of the agent under the same ID." (c) Decisively, resume is *architecturally wrong
   here*: the coordinator exists to DISCARD its slice's firehose on return, so resuming one
   re-animates exactly what it exists to destroy. **The disk is the channel** — a correction
   committed to the plan file reaches a builder at its next task boundary (verified:
   `build-s2` self-corrected on the dropped `AdminAccessPort`, `2cf67e8cf5`). Do NOT re-open
   this by granting SendMessage; it was rejected on token-cost grounds by the user.
3. **Gate visibility** — reconfirm that a depth-1 blocker/gate bubble reaches the user only via
   the manager's re-presentation (it should — that's the whole reason gates stay at depth-0).

## Integration points dhruva must wire

- New `.claude/agents/task-coordinator.md` (persona + the contract above).
- `agent-delegation.md` routing table + domain-boundaries row.
- `references/agent-teams-pipeline.md` — where the coordinator sits in auto-chain (it becomes
  the auto-chain *driver* between gates; the manager delegates the between-gate table to it).
- `dev-loop.md` / manager persona — the manager now delegates the inner loop to the
  coordinator instead of driving worker spawns directly.
- Manager memory — record the new delegation pattern.

## Verdict

Build it as a per-slice, gate-respecting, ephemeral coordinator. It is the structural form of
the retro's #1 fix and folds in #3 for free. Verify the nesting/notification behavior first.
