# Optimization Proposal — config changes to land the REF-001 session retro

**Author:** manager · **Date:** 2026-07-06 · **Owner of encoding:** dhruva (all are `.claude/`
config). **Constraint:** user at weekly usage cap (resets Jul 9) — batch these; don't spend
piecemeal. Ranked by impact (★★★ highest). #1 already dispatched; rest pending.

Two independent cost axes (they stack):
- **Token COUNT** — how much context is re-read per turn (#1, #3, #4, #8)
- **Token PRICE** — cost per token for a chunk of work (#2, #6)

---

## ★★★ #1 — Task-coordinator (offload the per-task firehose)  — DISPATCHED
Full spec: `.claude/proposals/task-coordinator-agent-design.md` (dhruva encoding now).
Files: NEW `agents/task-coordinator.md` · `rules/agent-delegation.md` (routing + boundaries) ·
`references/agent-teams-pipeline.md` (between-gate driver) · `rules/dev-loop.md` (manager
delegates inner loop) · `agents/manager.md` + manager memory (delegation pattern).
**Precondition:** dhruva verifies depth-1→depth-2 nesting + notification routing FIRST.

## ★★★ #2 — Per-task model-tier routing (cheap to write, frontier to review)
- `skills/task-breakdown/SKILL.md` — tag each task with a **tier** (mechanical | judgment)
  beside its S/M/L size. Signal = reasoning density, not file count.
- `agents/task-coordinator.md` — the router: spawn each worker at its tagged tier (Agent
  `model` param). This is where #2 lives operationally (composes with #1).
- NEW `rules/model-routing.md` (or a section in `dev-loop.md`) — the policy: **cheapen the
  writing, never the judging** (reviewer/security/architect/manager stay frontier);
  consequence-bearing tasks (tenancy/gating/payments) stay mid-tier + keep security review;
  **when in doubt → frontier** (a rework cycle costs more than the model saving). Cite the
  configio-tenancy-3× precedent as the cautionary anchor.

## ★★ #3 — Suppress idle-heartbeat narration
- Largely absorbed by #1 (worker pings route to the coordinator, not the manager/user).
- Residual: `agents/manager.md` + `rules/agent-interaction.md` — "do NOT emit a user-facing
  turn for idle pings from completed/superseded teammates; act only on critical-path
  completion or actionable failure."
- VERIFY: whether a settings.json hook can filter idle notifications at source (manager's own
  lane — settings/hooks not delegated). If hookable, prefer the hook over prose.

## ★★ #4 — Pass paths, not payloads (leaner spawn prompts)
- `references/agent-teams-pipeline.md` **Clarity Cascade Template** — amend: cite file PATHS
  the agent reads on demand; paste ONLY the decision-delta, never whole ADRs/studies inline.
- `agents/manager.md` + `agents/architect.md` — spawn-prompt discipline line.

## ★★ #5 — Scale review seats to NOVELTY, not raw file count
- `references/agent-teams-pipeline.md` **Review Team** — current trigger "6+ files → team."
  Amend: N near-identical files (e.g. 10 pattern-guards) = 1 reviewer, not 10. Scale seats to
  distinct-concern count. Smaller scopes also survive flaky infra better (less re-run exposure).

## ★★ #6 — Model/credit pre-flight + fail-fast
- Agent defaults already swapped (architect/manager/dhruva → opus) — DONE this session.
- `agents/manager.md` memory — lesson: on FIRST credit/model failure, swap model immediately;
  never respawn into the same wall (this session lost ~several runs to Fable before the swap).

## ~~★★ (bonus) SendMessage-resume over respawn-fresh~~ — **REJECTED (2026-07-16)**
- ~~`agents/manager.md` + `agents/task-coordinator.md` — resume a teammate's OWN interrupted
  task via `SendMessage` (context intact, no re-orientation cost); fresh spawn only for NEW
  work (where stale context would be a liability). This session respawned everywhere, paying
  orientation cost even where resume was cheaper.~~
- **Do not re-land this.** It WAS encoded (`manager.md:102`, `task-coordinator.md:108`) and has
  now been reverted. It backfires on every count: (a) neither agent is granted `SendMessage`
  (the `tools:` allowlist gates it for subagents), so it instructed a capability that does not
  exist; (b) "context intact" is unverified — a resume "starts a new run under the same ID";
  (c) it contradicts the whole design — the coordinator exists to DISCARD its firehose on
  return, so resuming one keeps alive what it exists to destroy. **The respawn this proposal
  called waste was the design working**: a fresh spawn re-reads ~30k of tasks + ADR and carries
  no prior transcript — cheaper than carrying the firehose. Steer in-flight work via the disk
  (commit the correction; the builder self-corrects at its next task boundary — verified,
  `2cf67e8cf5`), and **rule early**, since corrections land at boundaries, not instantly.

## ★ #7 — Front-load scope at intake
- `skills/intake-requirement/SKILL.md` — a Step prompt: "what else should this capture / any
  build-order or ownership preference?" to surface CR-1/CR-2-style additions BEFORE design
  hardens (both REF-001 change-requests arrived post-design → halt + re-plan + respawn).

## ★ #8 — Status from cache, not on-demand dashboards
- `agents/manager.md` + `skills/feature-status/SKILL.md` — answer "status?" from the last
  computed status-strip; recompute only on real state change, not per user prompt.

---

## Suggested execution order (one batched dhruva pass after the reset)
1. Finish #1 (in flight) — it's the spine; #2/#3 hang off it.
2. #2 model-routing — fold into the coordinator + task-breakdown (biggest cost lever after #1).
3. #4 + #5 — cheap prompt/review-scope edits, high frequency.
4. #3 + #6 + resume — manager-persona/memory lines.
5. #7 + #8 — intake + status polish.

Batch 2–8 into ONE dhruva session (single-writer on config; avoids repeated config-context
reloads). Verify #1's nesting precondition before relying on the coordinator.
