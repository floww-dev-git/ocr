# Document Intelligence POC

A municipal building-permission scrutiny workspace. An officer attaches the
documents filed with an application; the system reads them, compares what it read
against what the applicant declared, and asks the issuing department to confirm
what it holds. The officer stays the decision-maker throughout.

**Eleven document types are implemented**: PAN, Aadhaar and driving licence
(identity); sale deed and link document (registration); the encumbrance
certificate, land conversion certificate, market value certificate, pattadar pass
book and occupancy rights certificate (land/revenue); and the Irrigation NOC
(clearance). The catalog declares sixteen in all; anything else is identified,
marked unsupported, and left for the officer with a warning rather than silently
ignored.

Six of the eleven have no issuing department to ask — the Irrigation NOC and the
five land/revenue documents. For those, verification reports that there was nothing
to ask and leaves the confirmation to the officer. ADR-011 records why that is a
check of its own rather than a skipped step; ADR-012 adds the land/revenue
documents, including the encumbrance certificate's deliberate downgrade from IGRS to
manual-only for now.

### Aadhaar capability showcase

The Aadhaar is the worked example of the *range* of what the platform can do to a
document, rather than one check repeated. A single showcase application
(**BN/2026/0601**) holds the applicant's true identity, and a gallery of synthetic
specimens is judged against it — each engineered to demonstrate one capability:
real field extraction with confidence and provenance, a Verhoeff **checksum**, a
**QR-vs-print** integrity check, a **scan-quality** judgement, cross-checks against
the application, and issuer verification. The **Demo** menu lists the scenarios and
runs each in one click. Full walkthrough: `document_scrutiny/docs/features/
pan-document-verification/aadhaar-showcase-demo.md`; design and honest boundaries in
ADR-013. The specimens are synthetic and watermarked "SPECIMEN — NOT A REAL
AADHAAR"; no real PII.

```bash
# generate the specimens once (deterministic; no PII)
cd backend && uv run python scripts/generate_aadhaar_specimens.py

# run the showcase on real Gemini with the mock safety net under it, so a dropped
# network or spent key cannot hard-fail the demo on stage
EXTRACTION_MODE=gemini EXTRACTION_FALLBACK=1 GEMINI_API_KEY=... \
  DI_SERVER_PORT=8000 uv run uvicorn config.asgi:application --port 8000
```

`EXTRACTION_FALLBACK=1` puts the mock reader under Gemini: it is used only when
Gemini cannot run at all (a failure or a missing key), never to paper over a
genuinely unreadable document.

## Running it

Two processes. The backend must be served over ASGI, because the analyze endpoint
streams.

```bash
# terminal 1 — backend
cd backend
EXTRACTION_MODE=mock DI_SERVER_PORT=8000 uv run uvicorn config.asgi:application --port 8000

# terminal 2 — frontend
cd frontend
npm install
npm run dev          # http://127.0.0.1:5173
```

`EXTRACTION_MODE` selects the reader:

- `mock` — deterministic sample reads keyed off the application id. No API key needed.
- `gemini` — real extraction (the default). Needs `GEMINI_API_KEY`:
  ```bash
  set -a; source ../sale_deed_poc/build/poc/.env; set +a
  EXTRACTION_MODE=gemini DI_SERVER_PORT=8000 uv run uvicorn config.asgi:application --port 8000
  ```

The frontend proxies `/api` and `/mock` to `DI_BACKEND_ORIGIN`
(default `http://127.0.0.1:8000`), so the stream and the uploads are same-origin
and there is no CORS layer to configure.

## The demo

Pick **BN/2026/0377** — the seeded mismatch. Attach any `.jpg`, press
**Read and check**, and the four steps run: identify, read, compare, ask the
department.

It settles on *needs a look* with two open items: the name was misread, and the
Income Tax service holds the PAN but does not agree on the name.

1. Correct the name to `MOHAMMED IRFAN SIDDIQUI`. The name check settles, but the
   thread **stays** in attention — an officer's edit cannot change what the
   department holds.
2. Open **Checks**, and mark the department's answer *Verified by hand*. Now the
   thread reads clear. Note the check still shows *needs a look* with its original
   title: the officer's override is recorded beside the machine's verdict, never
   on top of it.
3. **Write the note.** It reports what was read, what is open, and the
   recommendation. Change anything afterwards and the note is marked out of date.

Use the **Demo** menu to force the department to never respond, then run again:
the check comes back *could not check* after a genuine three-second wait, with the
retry offered. Correct the name, set the service back to normal, and retry — it
confirms. Retry once more and it is refused, because there is nothing left to ask.

## Checking it

```bash
cd backend  && uv run pytest -q            # 1089 tests
cd frontend && npm test                    # 216 tests
cd frontend && npm run build               # typecheck + bundle

# end to end against a running backend, no mocks anywhere:
cd frontend && npm run verify:live
```

`verify:live` drives the real frontend modules — API client, SSE reader, run
reducer — against real Django, and asserts the whole officer story including the
forced-timeout path. It is the check that catches a contract drifting between the
two halves.

The backend also ships a curl walkthrough of the same story:

```bash
cd backend && BASE=http://127.0.0.1:8000 bash scripts/demo_officer_actions.sh
```

## How it is laid out

`backend/` is Django under Clean Architecture, six apps, per `.claude/rules/`.
Domain and interactor layers import no Django, no logger, and no storage
implementation — enforced by grep in CI-in-spirit and by the repo's quality gate.

| app | holds |
| --- | --- |
| `document_catalog` | document types, field specs, seeded applications |
| `document_extraction` | reading a document (mock and Gemini behind one port) |
| `document_verification` | talking to the mocked Income Tax service over real HTTP |
| `mock_issuer_services` | that service, so the call is a genuine network hop |
| `document_scrutiny` | the checks, the run, and the officer's actions |
| `api` | the composition root: URLs, views, wiring |

`frontend/` is React + Tailwind with ShadCN-style components copied in.
`src/api/contracts.ts` is the single written-down copy of the server's wire
shapes; `src/scrutiny/statusVocabulary.ts` is the single place a machine status
becomes words an officer reads.

Design decisions live in
`backend/document_scrutiny/docs/features/pan-document-verification/`:
`prd.md` (AC1–AC11), `flows.md` (five flows), and thirteen ADRs. ADR-008 records the
findings of the backend review, including what was deliberately left unfixed;
ADR-009 through ADR-012 record each document type added after PAN; ADR-013 records
the Aadhaar capability showcase.

## Known limits

- State is in memory. Restarting the backend loses open scrutinies. The storage
  sits behind an `abc` interface, so swapping in the ORM is a one-class change.
- Two analyze streams on one thread duplicate the extraction and the department
  call. Recorded in ADR-008; needs a per-thread lock the in-memory store lacks.
- Page images are not rendered in the Document tab — nothing produces them yet.
