#!/bin/bash
# Session stop: capture state snapshot for next session
TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null)
FEATURE_CONTEXT="$TOPLEVEL/feature-context.md"

if [ -f "$FEATURE_CONTEXT" ]; then
  echo "⚠ Update feature-context.md with current progress before closing."
  echo ""
  echo "State snapshot:"
  echo "  Branch: $(git branch --show-current 2>/dev/null)"
  CHANGES=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  echo "  Uncommitted files: $CHANGES"
  if [ "$CHANGES" -gt 0 ]; then
    git status --short 2>/dev/null
  fi
fi
