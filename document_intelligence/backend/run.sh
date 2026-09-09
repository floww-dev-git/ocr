#!/usr/bin/env bash
# Start the Document Intelligence backend on http://localhost:8000
# Served over ASGI (not `manage.py runserver`) because the analyze stream is SSE,
# and StreamingHttpResponse only supports async iterators under ASGI.
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

EXTRACTION_MODE="${EXTRACTION_MODE:-gemini}"
if [[ "$EXTRACTION_MODE" == "gemini" && -z "${GEMINI_API_KEY:-}" ]]; then
  echo "⚠  EXTRACTION_MODE=gemini but GEMINI_API_KEY is not set."
  echo "   Copy .env.example → .env and add your key, or run with EXTRACTION_MODE=mock."
fi

exec uv run uvicorn config.asgi:application --reload --port 8000
