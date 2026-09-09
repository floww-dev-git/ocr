#!/bin/bash
# PreCompact hook: saves feature context state before compaction wipes context
# Profile: standard+ (skipped in minimal)
PROFILE="${CLAUDE_HOOK_PROFILE:-standard}"
if [[ "$PROFILE" == "minimal" ]]; then exit 0; fi

TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null)
# Canonical home: <app>/docs/features/<slug>/feature-context.md (branch-matched);
# legacy fallback: repo root.
BRANCH=$(git branch --show-current 2>/dev/null)
FEATURE_CONTEXT=""
for f in "$TOPLEVEL"/*/docs/features/*/feature-context.md; do
    [ -f "$f" ] || continue
    if [ -n "$BRANCH" ] && grep -q "$BRANCH" "$f" 2>/dev/null; then
        FEATURE_CONTEXT="$f"; break
    fi
    [ -z "$FEATURE_CONTEXT" ] && FEATURE_CONTEXT="$f"
done
[ -z "$FEATURE_CONTEXT" ] && FEATURE_CONTEXT="$TOPLEVEL/feature-context.md"

if [ -f "$FEATURE_CONTEXT" ]; then
    echo "=== Pre-Compaction State Snapshot ==="
    echo "Branch: $(git branch --show-current 2>/dev/null)"
    echo "Uncommitted files: $(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')"
    echo "Staged files: $(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')"
    echo "Feature context: $FEATURE_CONTEXT"
    echo ""
    echo "REMINDER: Update feature-context.md with current task progress before compaction completes."
fi

exit 0
