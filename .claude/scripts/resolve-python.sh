#!/bin/bash
# Resolve a WORKING python interpreter for this repo, and say which one.
#
# WHY: this worktree carries a stub venv/ (31 packages, no Django) that SHADOWS
# the real interpreter in the sibling checkout. On 2026-07-20 two coordinators
# AND the manager concluded "no environment exists" and escalated it to the user
# as a hard blocker. It wasn't — workflow_engine/tests/ runs 428 green on the
# sibling interpreter. A venv that EXISTS is not a venv that WORKS, and a
# populated __pycache__ proves nothing: .pyc files are written at COMPILE time,
# before the import that fails.
#
# The probe is the proof. Never infer an environment from the filesystem.
#
# Usage:  .claude/scripts/resolve-python.sh          # print the interpreter path
#         $(.claude/scripts/resolve-python.sh) -m pytest workflow_engine/tests/
# Exit 1 + the full probe ledger when nothing works — an escalation to the user
# must carry that ledger, not a guess.

probe() {
  [ -x "$1" ] || return 1
  "$1" -c 'import django' >/dev/null 2>&1
}

CANDIDATES=()
[ -n "$VIRTUAL_ENV" ] && CANDIDATES+=("$VIRTUAL_ENV/bin/python")
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
CANDIDATES+=("$REPO_ROOT/venv/bin/python")
# Sibling checkouts of the same project — worktrees routinely lack their own venv
for sibling in "$(dirname "$REPO_ROOT")"/*/venv/bin/python; do
  CANDIDATES+=("$sibling")
done

LEDGER=""
for candidate in "${CANDIDATES[@]}"; do
  if probe "$candidate"; then
    echo "$candidate"
    exit 0
  fi
  if [ -x "$candidate" ]; then
    LEDGER="$LEDGER  $candidate — exists but cannot import django\n"
  else
    LEDGER="$LEDGER  $candidate — not present\n"
  fi
done

{
  echo "No working interpreter found. Probed:"
  printf "%b" "$LEDGER"
  echo "Each candidate was probed with 'python -c \"import django\"' — this ledger"
  echo "is evidence, not inference. Include it if you escalate to the user."
} >&2
exit 1
