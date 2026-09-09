# Recommendation — collapse `## Ambiguity Resolution` in agent-delegation.md

Status: RECOMMENDATION ONLY. Wrote **only** this file; edited nothing else.

## 1. Best-practice verdict + source

**The harness routes on agent `description` fields. Disambiguation belongs there — as per-agent
when-to-use + when-to-defer-to-sibling lines — not in a central table.**

Binary-confirmed (`~/.local/share/claude/versions/2.1.205`):
- The agent roster (each agent's `description`) is injected into context as the router; the model
  matches the user's message to a description and delegates (confirmed in prior cleanup pass).
- Verbatim harness instruction to the model:
  > "if the agent description mentions that it should be used proactively, then you should try
  > your best to use it without the user having to ask for it first."

This mirrors Anthropic's official subagent guidance (docs.claude.com — *Subagents*): the
`description` is what Claude uses to pick a subagent; make it detailed, specific, and
non-overlapping, and state boundaries explicitly. A central disambiguation table is redundant
with (and drifts from) the descriptions the harness actually reads.

**Manager's prior instinct is correct** — push each disambiguation into the two agents it
separates, relocate the implement fast-path, keep the two non-localizable judgments as rules.
One correction below: bullet 1 splits (its example moves, its tie-break stays).

## 2. Per-bullet verdict

| # | Bullet | Verdict | Target + edit |
|---|---|---|---|
| 1a | "prefer named agent" | **KEEP (rule)** | Meta tie-break — explicit `@name`/"hey X" beats a phrase match. Not localizable to any one description. One line. |
| 1b | "then more specific match (review payments code → security)" | **MOVE** | Redundant: `security.md` already carries `review payments code`. Add a defer line to `reviewer.md` (below). |
| 2 | ".claude/ config → dhruva" | **KEEP (rule)** | Path-based hard override — fires even with NO config trigger word ("edit this file" pointing at a `.claude/` path). A description match can miss it. Genuinely safer as a rule; also backed by `config-delegation.md`. |
| 3 | "review" → reviewer (code) / manager (requirements) | **MOVE** | One-directional conflict: `reviewer.md` claims `review feature`, which can grab a requirements review. Add a defer line to `reviewer.md`. Manager needs no edit (it doesn't claim "review code"). |
| 4 | "implement + complete plan → developer (fast-path)" | **RELOCATE (delete as dup)** | Already present in the **Pre-Implementation Gate** section: *"Skip gate when… complete plan provided (user stories + AC + task breakdown), or references an approved ADR."* Drop the bullet. |
| 5 | "test" → tester (pytest) / scout (gamma) | **MOVE** | Mostly already in descriptions (`tester.md`: "Does NOT write unit-RED… does NOT review code"; `scout.md`: gamma triggers). Add reciprocal defer lines to both. |
| 6 | "still ambiguous → ask the user" | **KEEP (rule)** | Safety-net fallback, not localizable. One line. |

## 3. Proposed end-state — `## Ambiguity Resolution` (6 bullets → 3 lines)

```markdown
## Ambiguity Resolution

Boundaries live in each agent's `description` (the harness routes on them) — read the roster, pick
by fit. Three residual judgments are not localizable to any single agent and stay here:

- **Explicit address wins** — `@name` / "hey <agent>" beats a competing trigger-phrase match.
- **`.claude/` path → `dhruva`** — any create/modify of a `.claude/` config file routes to dhruva,
  even with no config trigger word present (hard override; see `config-delegation.md`).
- **Still ambiguous → ask the user.**
```

(The implement fast-path is dropped — it already lives in **Pre-Implementation Gate** as the
skip-gate clause. No relocation edit needed; just delete the bullet.)

## 4. Exact description edits (`.claude/agents/*.md`)

Only **two** agents need edits (append to the `description` string, before the closing quote):

**`reviewer.md`** — append after the current `Triggers: …before merge.`:
> ` Defer: reviewing requirement/story scope (not code) → manager; changes touching payments/auth/iam/tdr/bps or other sensitive paths → security.`

**`tester.md`** — append after `…test-writer (legacy alias).`:
> ` Defer: running live end-user flows against gamma → scout.`

**`scout.md`** — append after `…draft gamma test plan.`:
> ` Defer: writing pytest unit/integration tests → tester.`

No edit needed:
- `security.md` — already carries `review payments code` + sensitive-path triggers (absorbs 1b).
- `manager.md` — doesn't claim "review code"; the reviewer-side defer covers bullet 3 fully.
- `developer.md` — fast-path handled by Pre-Implementation Gate (bullet 4).
- `dhruva.md` — bullet 2 stays a rule (path override), not a description line.

## 5. Bullets to KEEP as rules (and why)

- **1a "explicit address wins"** — a cross-agent tie-break; no single description can encode
  "beat a sibling's phrase match."
- **2 ".claude/ → dhruva"** — the one bullet genuinely *safer* as a rule than in a description:
  it must fire on a bare path reference with no config trigger word, which description-matching
  can miss. Flagged per the risk check.
- **6 "ask the user"** — global fallback.

## 6. Risk check

- Pushing 1b, 3, 5 into descriptions routes **reliably**: the harness injects the full roster, so
  reciprocal defer lines (reviewer→security/manager, tester↔scout) are visible at pick time and
  steer both away from the wrong seat and toward the right sibling. This is exactly the documented
  pattern.
- **One bullet is safer as a rule, not a description: #2 (`.claude/` → dhruva).** Descriptions
  match on phrasing; a request like "edit `.claude/rules/foo.md`" carries no config trigger word,
  so a pure description match could route it to `developer`. The path-based override must stay an
  explicit rule. Kept above.
- Net: 6 prose bullets → **3 rule lines + 3 one-clause description appends across 2… well, 3 agent
  files**. Always-on line count drops; the routing signal moves to where the harness actually reads
  it; drift risk (table vs descriptions) is eliminated.

## Confirmation
Wrote ONLY `.claude/proposals/ambiguity-resolution-rec.md`. Did not touch `agent-delegation.md`,
the audit doc, dhruva memory, or any agent file (single-writer respected).
