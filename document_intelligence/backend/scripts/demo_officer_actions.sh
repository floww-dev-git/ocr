#!/usr/bin/env bash
# Walks flows.md Flow 2 over real HTTP: a misread name is corrected, the thread
# stays in attention because the department still disagrees, and only the
# officer's own sign-off on the issuer answer clears it.
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8000}"
APPLICATION="${APPLICATION:-BN/2026/0377}"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

jqr() { python3 -c "import json,sys;d=json.load(sys.stdin);print(eval(sys.argv[1],{'d':d}))" "$1"; }

step() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

step "open a thread on $APPLICATION"
THREAD_ID=$(curl -sS -X POST "$BASE/api/threads" \
  -H 'Content-Type: application/json' \
  -d "{\"applicationId\":\"$APPLICATION\"}" | jqr "d['threadId']")
echo "thread: $THREAD_ID"

step "attach a PAN card"
printf 'not a real scan, the mock reader keys off the filename' > "$WORK_DIR/pan_card.jpg"
DOCUMENT_ID=$(curl -sS -X POST "$BASE/api/threads/$THREAD_ID/documents" \
  -F "files=@$WORK_DIR/pan_card.jpg" | jqr "d['documents'][0]['documentId']")
echo "document: $DOCUMENT_ID"

step "analyze (SSE)"
curl -sSN "$BASE/api/threads/$THREAD_ID/analyze" | grep -E '^event:|"threadStatus"' \
  | sed 's/\(.\{150\}\).*/\1…/' | tail -12

step "state after the run"
curl -sS "$BASE/api/threads/$THREAD_ID/note" | jqr "d['text']"

step "officer corrects the misread name"
curl -sS -X PATCH "$BASE/api/threads/$THREAD_ID/documents/$DOCUMENT_ID/fields/name" \
  -H 'Content-Type: application/json' \
  -d '{"value":"MOHAMMED IRFAN SIDDIQUI"}' \
  | jqr "('changed: %s | name check: %s | thread: %s | open: %s' % ([c for c in d['changedCheckIds']], [c['status'] for c in d['document']['checks'] if c['checkId'].endswith(':name')][0], d['summary']['threadStatus'], [i['text'] for i in d['summary']['openItems']]))"

step "officer signs off the issuer answer by hand"
curl -sS -X POST "$BASE/api/threads/$THREAD_ID/checks/$DOCUMENT_ID:issuer/resolve" \
  -H 'Content-Type: application/json' \
  -d '{"action":"manual"}' \
  | jqr "('check status kept: %s | manual: %s | thread: %s | open: %s' % (d['check']['status'], d['check']['manual'], d['summary']['threadStatus'], d['summary']['openItems']))"

step "officer confirms the fields"
curl -sS -X POST "$BASE/api/threads/$THREAD_ID/documents/$DOCUMENT_ID/confirm" \
  | jqr "('confirmed: %s | confirmedDocumentCount: %s' % (d['document']['confirmed'], d['summary']['confirmedDocumentCount']))"

step "the note now reads differently"
curl -sS "$BASE/api/threads/$THREAD_ID/note" | jqr "d['text']"

step "forced ITD timeout: a second thread, override set before the run"
THREAD_2=$(curl -sS -X POST "$BASE/api/threads" \
  -H 'Content-Type: application/json' \
  -d "{\"applicationId\":\"$APPLICATION\"}" | jqr "d['threadId']")
curl -sS -X PUT "$BASE/api/threads/$THREAD_2/service-overrides" \
  -H 'Content-Type: application/json' \
  -d '{"serviceOverrides":{"itd_pan":"timeout"}}' | jqr "d['serviceOverrides']"
DOCUMENT_2=$(curl -sS -X POST "$BASE/api/threads/$THREAD_2/documents" \
  -F "files=@$WORK_DIR/pan_card.jpg" | jqr "d['documents'][0]['documentId']")
curl -sSN "$BASE/api/threads/$THREAD_2/analyze" > "$WORK_DIR/stream2.txt"
python3 - "$WORK_DIR/stream2.txt" <<'PY'
import json, sys
for block in open(sys.argv[1]).read().split("\n\n"):
    lines = [l for l in block.split("\n") if l]
    if len(lines) < 2 or not lines[0].startswith("event: doc"):
        continue
    doc = json.loads(lines[1][len("data: "):])
    issuer = [c for c in doc.get("checks", []) if c["checkId"].endswith(":issuer")]
    if issuer:
        c = issuer[0]
        print(f"issuer check -> status={c['status']}  title={c['title']}")
        print(f"  detail: {c['detail']}")
        print(f"  latency: {c['issuerCall']['latencyMs']} ms")
        print(f"  document status: {doc['status']}")
PY

step "officer corrects the name, clears the override, then retries"
curl -sS -X PATCH "$BASE/api/threads/$THREAD_2/documents/$DOCUMENT_2/fields/name" \
  -H 'Content-Type: application/json' \
  -d '{"value":"MOHAMMED IRFAN SIDDIQUI"}' > /dev/null
curl -sS -X PUT "$BASE/api/threads/$THREAD_2/service-overrides" \
  -H 'Content-Type: application/json' -d '{"serviceOverrides":{}}' > /dev/null
curl -sS -X POST "$BASE/api/threads/$THREAD_2/documents/$DOCUMENT_2/retry-verification" \
  | jqr "('retry -> %s | %s | thread: %s' % (d['check']['status'], d['check']['title'], d['summary']['threadStatus']))"

step "retrying a department that already agreed is refused"
curl -sS -o "$WORK_DIR/refused.json" -w 'HTTP %{http_code} ' \
  -X POST "$BASE/api/threads/$THREAD_2/documents/$DOCUMENT_2/retry-verification"
jqr "d['errorCode']" < "$WORK_DIR/refused.json"
