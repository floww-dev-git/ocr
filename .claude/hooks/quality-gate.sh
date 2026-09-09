#!/bin/bash
# Post-tool hook: checks edited Python files for architecture violations
# Runs after Edit/Write on .py files — catches issues before self-review
# Profile: standard+ (skipped in minimal)
PROFILE="${CLAUDE_HOOK_PROFILE:-standard}"
if [[ "$PROFILE" == "minimal" ]]; then exit 0; fi

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi

VIOLATIONS=""

# Check 1: Cross-app imports (app internals imported from another app)
# Pattern: from <app>.storages|adapters|interactors|models|dtos|constants import ...
# Allowed: from <app>.app_interfaces import ... (that's the public API)
CROSS_APP=$(grep -nE '^from [a-z_]+\.(storages|adapters|interactors|models|dtos|constants)\.' "$FILE_PATH" 2>/dev/null | head -5)
if [[ -n "$CROSS_APP" ]]; then
  # Only flag if importing from a DIFFERENT app than the file's own app
  FILE_APP=$(echo "$FILE_PATH" | sed -n 's|.*/\([a-z_]*\)/\(storages\|adapters\|interactors\|models\|dtos\|constants\|tests\|app_interfaces\)/.*|\1|p')
  while IFS= read -r line; do
    IMPORT_APP=$(echo "$line" | sed -n 's|.*from \([a-z_]*\)\..*|\1|p')
    if [[ -n "$FILE_APP" && -n "$IMPORT_APP" && "$FILE_APP" != "$IMPORT_APP" ]]; then
      # Check it's not an app_interfaces import (those are allowed)
      if ! echo "$line" | grep -q 'app_interfaces'; then
        VIOLATIONS="${VIOLATIONS}\n⚠️ Cross-app import: ${line}"
      fi
    fi
  done <<< "$CROSS_APP"
fi

# Check 2: Bare except (catches everything including KeyboardInterrupt)
BARE_EXCEPT=$(grep -nE '^\s*except\s*:' "$FILE_PATH" 2>/dev/null | head -3)
if [[ -n "$BARE_EXCEPT" ]]; then
  VIOLATIONS="${VIOLATIONS}\n⚠️ Bare except: ${BARE_EXCEPT}"
fi

# Check 3: print/logger in interactors (business logic should not log)
if echo "$FILE_PATH" | grep -qE '/interactors/'; then
  PRINT_CALLS=$(grep -nE '^\s*(print\(|logger\.)' "$FILE_PATH" 2>/dev/null | head -3)
  if [[ -n "$PRINT_CALLS" ]]; then
    VIOLATIONS="${VIOLATIONS}\n⚠️ Logging in business logic: ${PRINT_CALLS}"
  fi
fi

# Check 4: parens-less get_bps_template_id under bps/configio/bps_template/
# get_bps_template_id is a @property in pipeline/data_store.py but a METHOD in
# bps_template/data_store.py. Calling it without () here yields a bound-method
# object (truthy, non-empty) -> the authorised-scope guard silently no-ops and
# the cross-tenant write proceeds. Only flag inside bps_template/ where it's a
# method; skip the assignment line in the data_store that defines it.
if echo "$FILE_PATH" | grep -qE 'bps/configio/bps_template/'; then
  PARENSLESS=$(grep -nE 'get_bps_template_id($|[^(_a-zA-Z])' "$FILE_PATH" 2>/dev/null \
    | grep -vE 'def get_bps_template_id|get_bps_template_id_for_gof_id|get_bps_template_id\(' \
    | head -3)
  if [[ -n "$PARENSLESS" ]]; then
    VIOLATIONS="${VIOLATIONS}\n⚠️ Parens-less get_bps_template_id (it's a METHOD here, not a property — add ()): ${PARENSLESS}"
  fi
fi

# Check 5: configio/populate write keyed on a CSV-row scope id without an
# authorised-scope comparison (cross-tenant WRITE guard, see configio-architecture.md).
# Heuristic, low-noise: only flags files that read a *_template_id / account_id /
# portal_id from a row dict (row.get / row[...] / record.get) AND never reference
# a data_store/authorised scope source in the same file. False negatives are fine;
# this is a nudge, not a gate.
if echo "$FILE_PATH" | grep -qE '/(configio|populate)/' && echo "$FILE_PATH" | grep -qvE '/tests?/'; then
  ROW_SCOPE=$(grep -nE '(row|record)(\.get\(|\[)["'\'']?[a-z_]*(template_id|account_id|portal_id)' "$FILE_PATH" 2>/dev/null | head -2)
  if [[ -n "$ROW_SCOPE" ]]; then
    HAS_AUTH=$(grep -cE 'authorised|authorized|data_store|get_account_id|get_bps_template_id' "$FILE_PATH" 2>/dev/null)
    if [[ "$HAS_AUTH" -eq 0 ]]; then
      VIOLATIONS="${VIOLATIONS}\n⚠️ ConfigIO scope from CSV row without an authorised-scope comparison — bind writes to the import context, not the row (see configio-architecture.md tenancy rule): ${ROW_SCOPE}"
    fi
  fi
fi

# Check 6: design-record prose in production source — a comment or docstring line
# citing an ADR / user story inside a non-test .py file (see clean-code.md "Comments").
# The design record lives in the ADR; a citation in source rots silently and is the
# reliable fingerprint of rationale prose pasted from the design doc.
# Measured 2026-08-13 over 49,815 repo .py files: 140 hits in 81 production files
# (0.16%) — and effectively all are the shape the rule forbids, so the FP rate is
# near-zero. Tests are EXCLUDED: 351 hits there are AC-traceability labels, which
# the rule explicitly encourages.
if echo "$FILE_PATH" | grep -qvE '/tests?/|/test_[^/]*\.py$|_test\.py$'; then
  # awk tracks triple-quote state so a citation inside a docstring is caught too,
  # while a citation inside real code (a constant, an f-string) is left alone.
  DESIGN_PROSE=$(awk '
    { line = $0 }
    # count triple-quote delimiters on this line to track docstring state
    { n = gsub(/"""/, "&", line) + gsub(/\x27\x27\x27/, "&", line) }
    {
      is_comment = ($0 ~ /^[ \t]*#/)
      cites = ($0 ~ /ADR-[0-9]/ || $0 ~ /US-[0-9]/)
      if (cites && (is_comment || indoc || n > 0)) print FILENAME ":" FNR ": " substr($0, 1, 110)
      if (n % 2 == 1) indoc = !indoc
    }
  ' "$FILE_PATH" 2>/dev/null | head -3)
  if [[ -n "$DESIGN_PROSE" ]]; then
    VIOLATIONS="${VIOLATIONS}\n⚠️ Design-record prose in source: an ADR/user-story citation belongs in the ADR, not a .py file (clean-code.md 'Comments — the design record does not live in source'). Delete the comment; keep the ADR: ${DESIGN_PROSE}"
  fi
fi

if [[ -n "$VIOLATIONS" ]]; then
  echo "---"
  echo "Quality gate violations in $(basename "$FILE_PATH"):"
  echo -e "$VIOLATIONS"
  echo "---"
fi

exit 0
