# ADR-006 — The analysis stream

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: PRD AC1, AC2, AC6, AC7, AC10

## Context

The prototype reveals its four stages with `setTimeout` — the timings are theatre, because there is no
work behind them. Here there is: a Gemini read takes seconds and an issuer call takes a second. The
officer needs to see progress as it happens, which is why the transport is SSE (ADR-001 D9).

Django's `StreamingHttpResponse` accepts an async iterator only under ASGI, and the work behind each
stage is blocking. This ADR records how those meet without the domain learning about either.

## Decisions

### D1 — The interactor yields events; the view frames them

`AnalyzeDocumentInteractor.analyze_document` is a generator of `AnalysisEventDTO`. It knows nothing about
SSE, HTTP, or `text/event-stream`. `ScrutinyStreamPresenter` turns one event into one frame, and the async
view pumps the generator. So the staging is testable as a list of DTOs — `list(interactor.analyze_document(...))`
— with no client, no server and no parsing.

### D2 — Two interactors: one per document, one per thread

`AnalyzeDocumentInteractor` handles a single document and emits only `step`, `doc` and `error`.
`AnalyzeThreadInteractor` loops the thread's unfinished documents, chains their events, then emits exactly
one `summary` and one `done`. It also **filters out any `done`** a per-document generator emits, so a
future change there cannot produce two terminators in one stream — there is a test for precisely that.

The closing summary re-reads the thread rather than reusing the state it started from, because the point of
the summary is to describe the finished state.

### D3 — Blocking work crosses into the event loop one item at a time

The view wraps `next(iterator)` in `sync_to_async(thread_sensitive=False)`. Each stage therefore runs on a
worker thread and the event loop stays free, which is what lets a frame reach the browser while the next
Gemini call is still running. `StopIteration` cannot cross that boundary, so a sentinel stands in for it.

### D4 — A tagged union, discriminated on `event_type`

`AnalysisEventDTO` carries one optional field per event kind. That is a tagged union, not the
flags-spread-over-optionals problem ADR-004 D7 warned about: the presenter switches on `event_type` first
and reads only the fields that kind defines. Separate DTO classes per kind would have typed it more
tightly at the cost of a `Union` return and `isinstance` branching in the presenter.

### D5 — The client is never shown an exception's text

Two levels. Inside the interactor, `ExtractionFailed` becomes a curated sentence naming the file. At the
view, `except Exception` logs the traceback and emits a generic sentence. A test asserts that a
`RuntimeError("psycopg2.OperationalError: secret host down")` reaches the client as neither `psycopg2` nor
`secret host` — the raw text is a server-side concern and library messages leak internals.

The view is the one place `except Exception` is allowed, and it logs and converts, per house exception rules.

### D6 — An unsupported document is *finished*, and carries a warning

Found by running it: leaving an unsupported document at `stage=identifying` made
`ScrutinySummary` report the thread as `running` forever, so the UI would spin with nothing behind it.

Marking it `done` alone would be worse — with no checks, the document derives `verified`, claiming a
document nobody read had been verified. So it is `done` **plus** one `warn` check,
`{document}:supported`. That is honest on three counts: the analysis really has finished, the officer
really does still have something to do, and it lands on the same worklist as every other open finding,
resolvable by acknowledging it or marking it verified by hand.

`unknown` — a document nobody could classify — takes the same path with its own wording, because
"Unknown document is not supported in this build" reads as nonsense.

### D7 — A finished document is never re-analyzed

`AnalyzeThreadInteractor` skips documents already at `done`, so re-opening the stream on a settled thread
costs one summary and one `done`. Without it, reconnecting an `EventSource` — which browsers do
automatically — would re-run extraction and re-bill every Gemini call.

## Consequences

- 25 tests cover the stream: event ordering, the check counts each stage reports, both failure paths, and
  the frames a broken stream still produces.
- Verified live with `curl -N` against the seeded mismatch: `identify → extract → checks → verify →
  summary → done`, 8 checks after `checks` and 9 after `verify`, closing on `thread=attention` with both
  the name warning and the issuer warning listed as open.
- `GZipMiddleware` is absent from `MIDDLEWARE`, so nothing compresses the stream. Adding it later must
  exclude this route or the frames will buffer.
