#!/bin/bash
# Sync settings.local.json from canonical source (main worktree)
CANONICAL_SETTINGS_LOCAL="$HOME/tdr/.claude/settings.local.json"
CURRENT_SETTINGS_LOCAL="$CLAUDE_PROJECT_DIR/.claude/settings.local.json"
if [ -f "$CANONICAL_SETTINGS_LOCAL" ]; then
  if [ ! -f "$CURRENT_SETTINGS_LOCAL" ] || ! diff -q "$CANONICAL_SETTINGS_LOCAL" "$CURRENT_SETTINGS_LOCAL" > /dev/null 2>&1; then
    cp "$CANONICAL_SETTINGS_LOCAL" "$CURRENT_SETTINGS_LOCAL"
    echo "⚡ Synced settings.local.json from canonical source"
  fi
fi

# Session start: restore structured state and show dashboard
TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null)

echo "=== Session Dashboard ==="

# Current branch
BRANCH=$(git branch --show-current 2>/dev/null)
echo "Branch: $BRANCH"

# Uncommitted changes
CHANGES=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "$CHANGES" -gt 0 ]; then
  echo "Uncommitted changes: $CHANGES files"
  git status --short 2>/dev/null
fi

# Feature context
FEATURE_CONTEXT="$TOPLEVEL/feature-context.md"
if [ -f "$FEATURE_CONTEXT" ]; then
  echo ""
  echo "--- Feature Context ---"
  cat "$FEATURE_CONTEXT"
  echo "--- End Context ---"
fi

# Python interpreter — probed, never inferred. A worktree's local venv/ may be a
# stub that shadows the real one in a sibling checkout (see resolve-python.sh).
PYTHON_BIN=$("$CLAUDE_PROJECT_DIR/.claude/scripts/resolve-python.sh" 2>/dev/null)
if [ -n "$PYTHON_BIN" ]; then
  echo ""
  echo "Python: $PYTHON_BIN (probed: imports django)"
  case "$PYTHON_BIN" in
    "$TOPLEVEL"/*) ;;
    *) echo "  NOTE: this worktree's own venv/ is unusable — use the path above." ;;
  esac
else
  echo ""
  echo "Python: NO working interpreter found — run .claude/scripts/resolve-python.sh"
  echo "  for the probe ledger before reporting an environment blocker."
fi

echo "========================"
