#!/usr/bin/env bash
# Start the Sale Deed Chain Validator prototype.
# Loads .env (for GEMINI_API_KEY) and serves on http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "⚠  GEMINI_API_KEY is not set. Copy .env.example → .env and add your key."
  echo "   (This build does real extraction — analysis will error without a key.)"
fi

exec uv run uvicorn app:app --reload --port 8000
