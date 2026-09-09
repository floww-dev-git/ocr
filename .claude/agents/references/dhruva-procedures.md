# Dhruva Procedural Reference

Detailed procedures for config auditing, authoring, and agent/team design.

## Audit Checks

### 1. Stale References
Search all `.claude/` files for references to paths that no longer exist:
```bash
# Patterns to check
grep -rn "\.claude/commands/" .claude/     # deleted directory
grep -rn "/home/floww-dev/" .claude/       # other developer paths
grep -rn "/Users/mm003/" .claude/          # other developer paths
```
Also verify that all `@.claude/rules/*.md` imports in skills point to existing files, and all `references/*.md` links in skills have matching files.

### 2. Duplication Detection
Compare content across layers. Flag when:
- A **rule** and a **skill** say the same thing (skill should reference rule with `@`)
- A **rule** and an **agent** say the same thing (agent should defer to rules)
- Two **skills** cover the same workflow (merge or differentiate)
- An **agent** embeds standards instead of loading skills

Grep for known indicator phrases that tend to get duplicated:
- `StorageMock`, `create_autospec`, `Factory Boy`, `assert_called_once_with`
- `Maximum.*50 lines`, `3 indentation levels`, `No flag arguments`
- `DTO-only`, `No Django model imports`, `InputObjectType`

### 3. Context Budget
Measure what's always loaded into every conversation:
- `CLAUDE.md` — target <100 lines
- Always-on rules (no `paths:` frontmatter) — track total lines
- Skill descriptions (always in context) — count total description length
- Agent descriptions — count total

Flag if total always-on context exceeds 500 lines.

### 4. Frontmatter Compliance
Check every skill's SKILL.md for:
- Has `description` (required for discoverability)
- Has `name` (recommended for clarity)
- Has `argument-hint` if it uses `$ARGUMENTS`
- Has `disable-model-invocation: true` for workflow skills (user-controlled timing)
- Has `allowed-tools` appropriate to its function
- Does NOT use invalid fields (`alwaysApply`, `globs` — those are for rules only)
- Does NOT list `MultiEdit` (not a standard tool — use `Edit`)

### 5. Skill-Rule Separation
Verify the correct boundary:
- **Rules** = standards, conventions, constraints (auto-loaded, declarative)
- **Skills** = workflows, procedures, step-by-step guides (invoked, imperative)
- **Agents** = personas with decision-making frameworks (delegate to skills/rules)

Flag skills that are purely declarative (should be rules) or rules that contain step-by-step procedures (should be skills).

### 6. Coverage Gaps
Check if the codebase has patterns not covered by any rule or skill:
- Are there app directories without any matching path-scoped rules?
- Are there common workflows developers do manually that could be skills?
- Are there recurring review feedback items that should be rules?

### 7. Memory Health
Check `.claude/agent-memory/` directories:
- Are MEMORY.md files up to date or empty?
- Do memory entries contradict current rules?
- Are there stale memories about deleted features or old patterns?

### 8. Skills Quality Checklist
Assess every skill against these 9 quality dimensions (source: Anthropic "Complete Guide to Building Skills for Claude", January 2026).

| # | Dimension | What to check | Pass criteria |
|---|---|---|---|
| 1 | **Description quality** | Frontmatter `description` field | States WHAT it does AND WHEN to use it (trigger phrases/scenarios) |
| 2 | **Troubleshooting** | Skill body or `references/` | Has a section for common errors, causes, and solutions |
| 3 | **Worked examples** | Skill body or `references/` | At least one "User says X -> Actions Y -> Result Z" example |
| 4 | **Metadata** | Frontmatter fields | Has `name`; optionally `author`, `version` for iteration tracking |
| 5 | **Success criteria** | Skill body or description | Documents "should trigger on X", "should NOT trigger on Y" |
| 6 | **Compatibility** | Frontmatter | Has `compatibility: claude-code` (optional but recommended) |
| 7 | **Iterative refinement** | Workflow steps | Built-in feedback loops (propose -> review -> revise), not single-pass |
| 8 | **Progressive disclosure** | File structure | SKILL.md is lean (<100 lines); details in `references/` or sibling files |
| 9 | **CLAUDE.md budget** | Root `CLAUDE.md` | Under 100 lines total |

**How to audit:** For each skill, score each dimension as GREEN (fully met), YELLOW (partially met), or RED (missing). Record results in Dhruva's MEMORY.md under "Skills Quality Baseline".

**Common remediation patterns:**
- RED on description -> Add trigger phrases to existing description
- RED on troubleshooting -> Add `## Troubleshooting` section or `references/troubleshooting.md`
- RED on worked examples -> Add `## Example` section with concrete scenario
- RED on progressive disclosure -> Extract long content into `references/` directory
- YELLOW on iterative refinement -> Add "propose -> wait for approval -> implement" gates

### 9. Anthropic Standards Compliance
Verify all config against `anthropic-config-standards.md`. For each category, check:

**Rules audit:**
- R1: Does every prohibition have a WHY rationale? (grep for bare "Do not" without explanation)
- R2: Are prohibitions framed positively where possible?
- R3: Any aggressive language? (grep for CRITICAL, MUST, NEVER, MANDATORY, VIOLATION, NON-NEGOTIABLE, HARD RULE)
- R4: Are rules path-scoped when they could be? (check if always-on rules only apply to specific directories)
- R5: Do hook-enforced rules note their enforcement? (after quality-gate hook exists)

**Agents audit:**
- A1: Do read-only agents have tool restrictions? (check frontmatter for allowed-tools)
- A2: Do all agents have anti-hallucination guidance?
- A3: Does the developer agent have scope discipline?
- A4: Do agents have collaborative voice with questioning patterns?
- A5: Do decision-making agents have self-learning loops?
- A6: Do reviewer/evaluator agents have calibration examples?

**Skills audit:**
- S1: Are all skills workflows (not domain knowledge)?
- S2: Do skills reference rules via @ instead of duplicating?
- S3: Is every SKILL.md under 100 lines with details in references/?
- S4: Do skills have propose→approve→implement gates?

**Cross-cutting audit:**
- C1: Is context awareness prompt in CLAUDE.md?
- C2: Is test protection in rules?
- C3: Does reviewer have confidence filtering?
- C4: Are parallelization guidelines in agent-interaction rule?

### 10. Agent Effectiveness Review
Check `.claude/agent-memory/dhruva/MEMORY.md` for the Agent Effectiveness Scorecard. For each agent:
- Correction frequency trending up? → Agent instructions need strengthening
- Same correction type recurring? → Missing rule or weak rule
- Delegation failures? → Clarity cascade template needs expansion
- No data? → Start tracking from this session

## Config Authoring Guide

### Deciding What to Create

| If the goal is... | Create a... | Why |
|---|---|---|
| Enforce a standard on all code | **Rule** (always-on) | Auto-loaded, declarative |
| Enforce a standard on specific files | **Rule** (path-scoped) | Only loads when matching files are touched |
| Define a repeatable workflow | **Skill** (user-invocable) | Step-by-step, invoked with `/skill-name` |
| Provide reference context | **Skill** (context loader) | Loads domain knowledge on demand |
| Define a persona that makes decisions | **Agent** | Delegates to skills/rules, has judgment |

### Rule Conventions (this repo)
- Location: `.claude/rules/<name>.md`
- Use `globs:` frontmatter to scope to specific file patterns when possible (reduces always-on context)
- Keep declarative — "what", not "how". No step-by-step procedures.
- Check for overlap with existing rules before creating:
  - `clean-code.md` — function size, naming, control flow, constants, comments, DRY
  - `clean-architecture.md` — layers, DTOs, app isolation, dependency inversion, app map
  - `exception-handling.md` — try/except rules, domain exception patterns
  - `testing.md` — test patterns, mocking, factories, assertions
  - `interactors.md` — interactor structure, validation, storage calls
  - `storages.md` — storage implementation patterns
  - `models.md` — Django model conventions
  - `graphql.md` — GraphQL schema, mutations, queries
- If the content fits an existing rule, extend it instead of creating a new file
- Target: each rule <200 lines

### Skill Conventions (this repo)
- Location: `.claude/skills/<name>/SKILL.md`
- Required frontmatter: `description` (concise, explains when to use)
- Required if user-invocable: `argument-hint` with `$ARGUMENTS` in body
- Required for workflows: `disable-model-invocation: true`
- Set `allowed-tools` appropriate to function (Read/Grep/Glob for context loaders, add Edit/Write for creators)
- Reference rules with `@.claude/rules/<name>.md` — NEVER duplicate rule content
- Keep SKILL.md concise (<100 lines). Put detailed reference material in sibling files (e.g., `references/`, `examples/`)
- Do NOT use `MultiEdit` in allowed-tools (not a standard tool — use `Edit`)
- Do NOT use `alwaysApply` or `globs` in skill frontmatter (those are rule-only fields)
- Add the skill to the Workflow Skills table in `CLAUDE.md` if user-invocable

### Agent Conventions (this repo)
- Location: `.claude/agents/<name>.md`
- Required frontmatter: `name`, `description` (include trigger phrases), `model`, `color` (unique per agent)
- Current colors in use: purple (dhruva), blue (developer), cyan (architect), red (reviewer), yellow (security), orange (manager)
- List `skills:` in frontmatter for skills the agent should load
- Agent body defines persona and decision framework — delegates to skills/rules for standards
- NEVER embed code standards in agent body — reference rules instead
- If the agent needs persistent memory, create `.claude/agent-memory/<agent-name>/MEMORY.md`

### Authoring Checklist (run before finalizing)
1. Does it overlap with an existing rule/skill/agent? -> Extend existing instead
2. Is it the right type (rule vs skill vs agent)? -> Check the decision table above
3. Is the frontmatter complete? -> Run Audit Check #4 mentally
4. Does it duplicate rule content? -> Use `@` references instead
5. Will it bloat always-on context? -> Path-scope if possible
6. Is it in CLAUDE.md workflow table? -> Add if user-invocable skill
7. Does naming follow conventions? -> kebab-case directories, descriptive names

## Agent & Team Design

### Design Process
1. **Understand the use case** — what's the goal, what decisions are involved, what's the workflow?
2. **Decompose into roles** — identify distinct responsibilities that need different expertise or judgment
3. **Choose the right pattern** — single agent, agent + skills, or multi-agent team
4. **Design the delegation flow** — who triggers whom, what data flows between them

### When to Use What

| Complexity | Pattern | Example |
|---|---|---|
| Single workflow, no judgment | **Skill** | `/write-interactor` — follows a template |
| Single workflow, needs judgment | **Agent** | `tester` — decides what to test, adapts to failures |
| Multiple workflows, one domain | **Agent + Skills** | `software-developer` — uses multiple skills based on context |
| Multiple domains, coordination needed | **Agent Team** | Feature build — one agent writes code, another writes tests, a third reviews |
| Continuous observation | **Agent + always-on rule** | `dhruva` — rule triggers delegation, agent does the work |

### Agent Design Principles
- **Single responsibility** — each agent owns one domain of judgment
- **Skill delegation** — agents use skills for repeatable steps, make decisions themselves for novel situations
- **Minimal overlap** — if two agents share >50% of their work, merge them or split differently
- **Clear triggers** — description must include when to invoke (trigger phrases + auto-trigger conditions)
- **Model selection** — `opus` for complex judgment, `sonnet` for fast/routine work
- **Memory per agent** — if an agent learns from experience, give it `.claude/agent-memory/<name>/`

### Team Design Principles
- **Coordinator pattern** — one agent orchestrates, delegates subtasks to specialist agents
- **Parallel independence** — agents in a team should be able to work without blocking each other
- **Shared rules, separate judgment** — all agents follow the same rules, but each has its own decision framework
- **Handoff protocol** — define what output one agent passes to the next (DTOs of the agent world)

### Current Agent Roster
Review before creating new agents to avoid overlap:
- **dhruva** (opus, purple) — system accelerator, config quality, proactive research, agent effectiveness monitoring
- **developer** (sonnet, blue) — feature implementation, bug fixes, dev loop (override to opus for complex tasks)
- **architect** (opus, cyan) — planning, ADRs, task generation
- **reviewer** (opus, red) — independent code review, structured findings
- **security** (opus, yellow) — security analysis, OWASP checks, sensitive flow review
- **manager** (opus, orange) — requirement analysis, feature orchestration, worktree management

## Development Observer Triggers

When running in observer mode after development work, check:

1. **After writing an interactor** — does the interactors rule cover the patterns used? Were there corrections that should become rules?
2. **After writing tests** — did the developer have to look up testing patterns manually? Should those be in the testing rule?
3. **After a code review** — are the review points things that rules should catch automatically?
4. **After fixing a bug** — should the fix pattern be documented in memory?
5. **After adding a new app/module** — does the app dependency map in `clean-architecture.md` need updating?

## Web Research for Best Practices

### Authoritative Sources (check these first)
- **Anthropic official docs**: `code.claude.com/docs/` — canonical reference for rules, skills, agents, hooks, memory
- **Anthropic engineering blog**: `anthropic.com/engineering` — official patterns and recommendations
- **Claude Code changelog**: check for new features that could improve the config

### Community Sources (validate against official docs)
- **GitHub repos**: `github.com/anthropics/claude-code` — official examples and issues
- **Top community configs**: `github.com/shanraisshan/claude-code-best-practice`, `github.com/trailofbits/claude-code-config`, `github.com/hesreallyhim/awesome-claude-code`
- **Builder.io blog** (Steve Sewell): practical tips from heavy usage
- **Dev.to / Medium**: community patterns (validate before adopting)

### Research Rules
- Always verify community advice against official Anthropic docs
- Note the source and date when saving research findings to memory
- If official docs contradict community advice, follow official docs
- Flag when a community pattern isn't documented officially (might be undocumented feature or misconception)
