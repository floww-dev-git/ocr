# Anthropic Config Standards

Checklist Dhruva applies when creating, reviewing, or auditing any .claude/ config. Every standard has a source. If a standard conflicts with project convention, project convention wins but the conflict should be documented.

Last reviewed: 2026-03-26

## References

Primary sources for further research:
- [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) — R1, R2, R3, A2, A3, C1, C4
- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — C2, O2
- [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps) — A4, A6, M1
- [Complete Guide to Building Skills for Claude](https://www.anthropic.com/engineering/claude-code-best-practices) — S3, S4
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) — R4, R5, A1, C3, O1

## Rules Standards

**R1: WHY Rationale** — Every prohibition includes a 1-line reason. Claude generalizes better from explained rules than bare prohibitions.
- Bad: "50 lines per function"
- Good: "50 lines per function — beyond this, functions have multiple responsibilities and become hard to test in isolation"
[Source: prompting best practices — add context](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#add-context-to-improve-performance)

**R2: Positive Framing** — Prefer "always do X" over "never do Y." Tell Claude what to do, not what to avoid. Use "Do not" for hard safety boundaries, but pair with the positive alternative.
- Bad: "NEVER use bare except"
- Good: "Always catch specific, expected exceptions with appropriate recovery logic — bare except swallows KeyboardInterrupt and hides bugs"
[Source: prompting best practices — format control](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#control-the-format-of-responses)

**R3: No Aggressive Language** — No CRITICAL, MUST, NEVER, MANDATORY, VIOLATION, NON-NEGOTIABLE, HARD RULE. Claude 4.6 overtriggers on aggressive prompts. The rules are strict; the tone is calm.
- Bad: "CRITICAL: MANDATORY GATE — NEVER skip this or it's a VIOLATION"
- Good: "Always route new features through the manager first. Skipping this leads to scope creep and rework."
[Source: prompting best practices — tool usage](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#tool-usage)

**R4: Path-Scope When Possible** — Rules that only apply to specific file types or directories use `paths:` frontmatter. Reduces always-on context budget. Target: <500 lines always-on.
[Source: ECC token optimization patterns](https://github.com/affaan-m/everything-claude-code/blob/main/docs/token-optimization.md)

**R5: Hook-Enforcement Annotation** — Rules with automated enforcement via hooks note it. Tells the developer what the system catches automatically vs what requires manual self-review.
[Source: ECC rule-hook integration pattern](https://github.com/affaan-m/everything-claude-code/tree/main/hooks)

## Agent Standards

**A1: Tool Restrictions** — Scope each agent's `tools:` frontmatter to what it actually needs; an over-broad grant is enforced only by prose, which the model can slip.
- **Correct key is `tools:`** (comma-separated, per docs). `allowed-tools:` is NOT a recognized key — it is silently ignored, so the agent inherits everything. (Real bug: `dhruva.md` used `allowed-tools:` and had all tools for months.)
- **An allowlist is complete-or-broken** — a tool omitted from `tools:` is unavailable (no inherit-all fallback). List every tool the agent uses.
- **Pure analysis agents** (reviewer, security, scout) → `Read, Grep, Glob, Bash`.
- **Orchestrator agents** (manager, dhruva) also need `Agent` (to spawn — *omitting it disables spawning entirely*), `Skill` (to invoke skills at runtime), `Write`/`Edit` (context files), and `AskUserQuestion` (gates). These are NOT read-only.
[Source: [Claude Code sub-agents docs](https://code.claude.com/docs/en/sub-agents#supported-frontmatter-fields) + [ECC agent conventions](https://github.com/affaan-m/everything-claude-code/tree/main/agents)]

**A2: Anti-Hallucination** — All agents read code before making claims about it. "I see X in the code" requires having Read the file first. Never speculate about entities, fields, enums, or file contents.
[Source: prompting best practices — minimizing hallucinations](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#minimizing-hallucinations-in-agentic-coding)

**A3: Scope Discipline** — Implement what's asked. Don't refactor adjacent code, add unrequested features, or create abstractions for hypothetical future needs. A bug fix doesn't need surrounding code cleaned up.
[Source: prompting best practices — overeagerness](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#overeagerness)

**A4: Collaborative Voice** — Agents are problem-solving companions, not instruction executors. Ask meaningful questions, challenge assumptions constructively, have personality. Each agent has a distinct voice appropriate to its domain.
[Source: harness design — sprint contracts and evaluator negotiation](https://www.anthropic.com/engineering/harness-design-long-running-apps)

**A5: Self-Learning Loop** — Every agent that makes decisions needs persistent memory at `.claude/agent-memory/<name>/`. Read on session start, update on session end. Promote recurring patterns to rules after 2+ occurrences.
Source: Project convention

**A6: Few-Shot Calibration** — Evaluator/reviewer agents need 2-3 example findings showing a good finding vs an over-flagged false positive. Calibration examples anchor judgment and prevent score drift across reviews.
[Source: harness design — evaluator calibration](https://www.anthropic.com/engineering/harness-design-long-running-apps)

## Skill Standards

**S1: Workflows Only** — Skills define step-by-step procedures. Domain knowledge goes in folder CLAUDE.md files (auto-loaded by proximity), not in skills. Never create "context-loader" skills.
Source: Project config-delegation rule

**S2: Reference Rules via @** — Skills reference rules with `@.claude/rules/<name>.md`. Never duplicate rule content. If a skill needs a standard, point to the rule.
Source: Project convention

**S3: Progressive Disclosure** — SKILL.md stays lean (<100 lines). Detailed reference material, patterns, and examples go in `references/` subdirectory. The skill body is the workflow; references are the knowledge.
[Source: Claude Code best practices — skills](https://www.anthropic.com/engineering/claude-code-best-practices)

**S4: Iterative Refinement** — Skills have propose → wait for approval → implement gates. Not single-pass execution. The user reviews before the agent commits to implementation.
[Source: Claude Code best practices — skills](https://www.anthropic.com/engineering/claude-code-best-practices)

## Cross-Cutting Standards

**C1: Context Awareness** — Agents don't stop work early due to token budget. Context is automatically compacted. Save progress to feature-context.md before compaction. Be persistent — complete tasks fully.
[Source: prompting best practices — context awareness](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#context-awareness-and-multi-window-workflows)

**C2: Test Protection** — Never remove, weaken, or skip existing tests. Tests are the contract. If a test fails, fix the code, not the test (unless the test itself is wrong, with clear explanation).
[Source: effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

**C3: Confidence Filtering** — Reviewers report findings at >80% confidence. Consolidate similar issues ("5 functions missing error handling" not 5 separate findings). Skip stylistic preferences unless they violate project conventions.
[Source: ECC code-reviewer](https://github.com/affaan-m/everything-claude-code/blob/main/agents/code-reviewer.md)

**C4: Parallelization** — Use parallel tool calls for independent operations. Background jobs for long-running tasks. Batch questions instead of serial round-trips. Maximum throughput without compromising correctness.
[Source: prompting best practices — parallel tool calling](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices#optimize-parallel-tool-calling)

## Operational Standards

**O1: Compaction at 75%** — Set `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=75`. Default 95% causes quality degradation in later turns. 75% balances conversation continuity with a safe buffer before the hard ceiling.
[Source: ECC token optimization](https://github.com/affaan-m/everything-claude-code/blob/main/docs/token-optimization.md)

**O2: Session Persistence** — Save structured state (branch, task, uncommitted files, test status) on session stop. Restore on session start. Run baseline tests before resuming implementation.
[Source: effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)

## Meta Standards

**M1: Periodic Harness Review** — Every component in the config encodes an assumption about what the model can't do. As models improve, strip scaffolding that's no longer load-bearing. Review after major model upgrades.
[Source: harness design for long-running apps](https://www.anthropic.com/engineering/harness-design-long-running-apps)

**M2: Measure Before/After** — Always show metrics when proposing config changes. Line counts, context budget impact, affected agents. No change without data.
Source: Project convention
