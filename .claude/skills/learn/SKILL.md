# Pattern Extraction (`/learn`)

Scan recent work for repeated patterns, corrections, and knowledge gaps — then propose rule, memory, or skill updates.

## When to Use

- After completing a feature (post-commit)
- When Dhruva's auto-trigger fires after development work
- When explicitly asked: "what should we learn from this?"

## Steps

1. **Scan recent activity** — check the last 10-20 commits and any agent memory files:
   ```bash
   git log --oneline -20
   ```
   Read `.claude/agent-memory/*/MEMORY.md` for all agents that have memory files.

2. **Identify learning signals** — look for:
   - **Repeated corrections** — same type of fix applied 2+ times across commits (e.g., "fix missing `.value`", "fix cross-app import")
   - **New patterns** — code patterns that appeared for the first time (new adapter style, new test pattern, new DTO convention)
   - **Review findings that rules should have caught** — if a reviewer or user flagged something that an existing rule covers but wasn't followed, the rule may need strengthening
   - **Knowledge gaps** — if an agent had to ask about something that should be documented (business logic, app conventions, entity relationships)

3. **Classify each finding**:

   | Signal | Action |
   |---|---|
   | Same code mistake caught 2+ times | Propose adding to relevant rule |
   | Same process gap flagged 2+ times | Propose adding to agent instructions |
   | User explicitly corrected an agent | Update that agent's memory AND instructions |
   | Review finding that rules should have caught | Propose strengthening the rule |
   | New convention not yet documented | Propose adding to folder CLAUDE.md or memory |
   | New workflow discovered | Propose creating a skill |

4. **Present findings** in this format:
   ```markdown
   # Learning Report

   ## Patterns Found
   - [Pattern]: [where observed] → [proposed action: rule/memory/skill/agent update]

   ## Proposed Changes
   1. **[Target file]** — [specific change]
      Rationale: [why this prevents future issues]

   ## No Action Needed
   - [Patterns that were one-off or already covered]
   ```

5. **Wait for approval** before making any changes. Once approved, delegate to Dhruva for implementation.

## Promotion Criteria

- 1 occurrence: record in agent memory as "observed, watching"
- 2 occurrences: promote to rule, agent instruction, or CLAUDE.md
- User says "remember this": promote immediately regardless of count
