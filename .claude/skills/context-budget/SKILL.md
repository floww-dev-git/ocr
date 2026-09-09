# Context Budget Diagnostic

Analyze the always-on context budget — line counts, bloat detection, and optimization suggestions.

## Steps

1. **Count always-on rules** — list all files in `.claude/rules/` that do NOT have `globs:` frontmatter (these load on every prompt):
   ```bash
   for f in .claude/rules/*.md; do
     if ! head -5 "$f" | grep -q 'globs:'; then
       lines=$(wc -l < "$f")
       echo "$lines $f"
     fi
   done | sort -rn
   ```

2. **Count path-scoped rules** — same but WITH `globs:` frontmatter:
   ```bash
   for f in .claude/rules/*.md; do
     if head -5 "$f" | grep -q 'globs:'; then
       lines=$(wc -l < "$f")
       echo "$lines $f"
     fi
   done | sort -rn
   ```

3. **Count CLAUDE.md files** — root + all folder CLAUDE.md:
   ```bash
   wc -l CLAUDE.md
   find . -name 'CLAUDE.md' -not -path './CLAUDE.md' -not -path './.claude/*' | xargs wc -l | sort -rn | head -20
   ```

4. **Count agent definitions**:
   ```bash
   for f in .claude/agents/*.md; do
     lines=$(wc -l < "$f")
     echo "$lines $f"
   done | sort -rn
   ```

5. **Count skills**:
   ```bash
   ls -d .claude/skills/*/SKILL.md | wc -l
   ```

6. **Present report**:
   ```markdown
   # Context Budget Report

   ## Always-On Context
   | Source | Lines |
   |---|---|
   | CLAUDE.md (root) | X |
   | Always-on rules | X (N files) |
   | **Total always-on** | **X** |

   Target: <500 lines. Status: [OK|OVER by X lines]

   ## Path-Scoped (loaded on demand)
   | Source | Lines |
   |---|---|
   | Path-scoped rules | X (N files) |
   | Folder CLAUDE.md | X (N files) |

   ## Agent Definitions
   | Agent | Lines |
   |---|---|
   [table]

   ## Top 5 Largest Always-On Rules
   [table — candidates for path-scoping]

   ## Suggestions
   - [Any rules over 50 lines that could be path-scoped]
   - [Any folder CLAUDE.md over 250 lines]
   - [Any agent over 200 lines]
   ```
