#!/bin/bash
# Post-tool hook: runs ruff check --fix on edited/written Python files
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE_PATH" == *.py ]]; then
  ruff check --fix "$FILE_PATH" 2>/dev/null || true
fi

exit 0
