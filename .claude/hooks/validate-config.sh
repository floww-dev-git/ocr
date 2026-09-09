#!/bin/bash
# Config validation: checks for dead references across .claude/ config
# Run manually: bash .claude/hooks/validate-config.sh
set -euo pipefail

CLAUDE_DIR=".claude"
ERRORS=0
WARNINGS=0

echo "=== Config Validation ==="

# Check 1: Skill names in CLAUDE.md workflow table resolve to actual skill directories
# Only check backtick-quoted skill refs like `/<name>` to avoid false positives
echo ""
echo "--- Skill References ---"
SKILL_REFS=$(grep -oE '`/[a-z][a-z0-9-]+`' CLAUDE.md 2>/dev/null | sed 's|[`/]||g' | sort -u)
for skill in $SKILL_REFS; do
  if [ -d "$CLAUDE_DIR/skills/$skill" ]; then
    if [ ! -f "$CLAUDE_DIR/skills/$skill/SKILL.md" ]; then
      echo "ERROR: Skill directory exists but missing SKILL.md: $skill"
      ERRORS=$((ERRORS + 1))
    fi
  else
    echo "WARN: Possible dead skill reference in CLAUDE.md: /$skill"
    WARNINGS=$((WARNINGS + 1))
  fi
done
echo "Skill references checked."

# Check 2: Agent frontmatter skill references resolve
echo ""
echo "--- Agent Skill References ---"
for agent_file in "$CLAUDE_DIR"/agents/*.md; do
  agent_name=$(basename "$agent_file" .md)
  # Extract skills from frontmatter (between --- markers)
  in_frontmatter=false
  in_skills=false
  while IFS= read -r line; do
    if [[ "$line" == "---" ]]; then
      if $in_frontmatter; then break; fi
      in_frontmatter=true
      continue
    fi
    if $in_frontmatter && [[ "$line" =~ ^skills: ]]; then
      in_skills=true
      continue
    fi
    if $in_skills; then
      if [[ "$line" =~ ^[[:space:]]*-[[:space:]]+(.*) ]]; then
        skill_name="${BASH_REMATCH[1]}"
        skill_name=$(echo "$skill_name" | tr -d '"' | tr -d "'")
        if [ ! -d "$CLAUDE_DIR/skills/$skill_name" ]; then
          echo "ERROR: Agent '$agent_name' references missing skill: $skill_name"
          ERRORS=$((ERRORS + 1))
        fi
      else
        in_skills=false
      fi
    fi
  done < "$agent_file"
done
echo "Agent skill references checked."

# Check 3: Agent memory directories exist for agents with self-learning sections
echo ""
echo "--- Agent Memory Directories ---"
for agent_file in "$CLAUDE_DIR"/agents/*.md; do
  agent_name=$(basename "$agent_file" .md)
  if grep -q 'agent-memory' "$agent_file" 2>/dev/null; then
    if [ ! -d "$CLAUDE_DIR/agent-memory/$agent_name" ]; then
      echo "WARN: Agent '$agent_name' references memory but directory missing: $CLAUDE_DIR/agent-memory/$agent_name/"
      WARNINGS=$((WARNINGS + 1))
    fi
  fi
done
echo "Agent memory directories checked."

# Check 4: Hook scripts referenced in settings.json exist and are executable
echo ""
echo "--- Hook Scripts ---"
HOOK_SCRIPTS=$(grep -oE '\$CLAUDE_PROJECT_DIR/[^"]+' "$CLAUDE_DIR/settings.json" 2>/dev/null | sed 's|\$CLAUDE_PROJECT_DIR/||')
for script in $HOOK_SCRIPTS; do
  if [ ! -f "$script" ]; then
    echo "ERROR: Hook script missing: $script"
    ERRORS=$((ERRORS + 1))
  elif [ ! -x "$script" ]; then
    echo "WARN: Hook script not executable: $script"
    WARNINGS=$((WARNINGS + 1))
  fi
done
echo "Hook scripts checked."

# Check 5: Rule files referenced via @.claude/rules/ in skills
echo ""
echo "--- Rule References in Skills ---"
RULE_REFS=$(grep -rhoE '@\.claude/rules/[a-z0-9-]+\.md' "$CLAUDE_DIR/skills/" 2>/dev/null | sort -u | sed 's|^@||')
for rule_path in $RULE_REFS; do
  if [ ! -f "$rule_path" ]; then
    echo "ERROR: Dead rule reference in skills: @$rule_path"
    ERRORS=$((ERRORS + 1))
  fi
done
echo "Rule references checked."

# Summary
echo ""
echo "=== Validation Summary ==="
echo "Errors: $ERRORS"
echo "Warnings: $WARNINGS"
if [ $ERRORS -gt 0 ]; then
  echo "STATUS: FAIL"
  exit 1
else
  echo "STATUS: PASS"
  exit 0
fi
