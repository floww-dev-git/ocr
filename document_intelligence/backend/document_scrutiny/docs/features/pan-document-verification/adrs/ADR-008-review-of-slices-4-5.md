# ADR-008 — Outcomes of the slices 4–5 backend review

Status: accepted
Date: 2026-09-08
Scope: findings from the deferred combined review of thread storage, document
intake, the analyze stream, and officer actions, and the decisions taken in
response.

## Context

Slices 4 and 5 were built across tasks 9–11 with a review deliberately deferred
to the end so it could judge the whole shape rather than three partial ones. Two
independent reviews were run: one for conformance to `.claude/rules/`, one
adversarial hunt for provable bugs. Both reproduced their findings by running
code, not by reading it. This ADR records what was wrong and what was decided,
because several of the fixes changed behaviour the earlier ADRs describe.

## D1 — An officer action is refused while the document is being read

**The bug (Critical, proved over HTTP).** `AnalyzeDocumentInteractor` read the
document once at the start and wrote results derived from that snapshot at each
stage. An officer edit landing mid-run returned `200` with `edited: true` and a
`pass` check, and was then overwritten seconds later with no trace it had ever
happened. The officer was actively misled, which is worse than any stale number.

**The decision.** `OfficerActionGuard.check_document_is_not_being_read` raises
`DocumentBusy` → `409 DOCUMENT_BUSY` for edit, sign-off, resolve and retry when
the document's stage is one of `identifying`, `extracting`, `checking`,
`verifying`. Stage already carried this fact, so no new state was introduced.

Rejected: merging officer-owned fields on write, or a revision counter with
compare-and-set. Both are the right answer for a multi-writer system and both are
more machinery than a single-officer POC can justify. Being told "wait, this is
still being read" is honest and cheap; being told "saved" and silently losing it
is neither. The fix is recorded here rather than in ADR-007 because it constrains
every action D1–D5 of that ADR describes.

## D2 — The document's own verdict is re-derived on every write

**The bug (High, proved twice).** `DocumentStateDTO.status` is derived from stage
plus checks. `ResolveCheckInteractor` and `RetryIssuerVerificationInteractor`
wrote with `dataclasses.replace` and never re-derived it, so a document whose only
`fail` check had been acknowledged still read `failed` while the thread badge next
to it read `clear`, and the note said `Fit to proceed`. On the retry path the stale
value was the harsher one: a document permanently reading `failed` whose evidence
no longer contained a failure — exactly the "verdict its own evidence disputes"
that ADR-001 D7 exists to forbid.

**The decision.** `ThreadRevision.save_document` now re-derives the document's
verdict through `DocumentProgress` before persisting. Putting it in the one
collaborator all four officer actions already funnel through means no future action
can forget. `ThreadRevision` existed because every action has a whole-thread
consequence (ADR-007 D7); it simply stopped one level short of the document.

The tests missed this because they asserted `change.check.status` and
`change.summary.thread_status` but never `change.document.status`. All three are
now asserted, at interactor and HTTP level.

## D3 — A field the officer clears keeps its check; a field never read still does not

**The bug (High, proved over HTTP).** Checks are skipped for empty field values,
which is right for a bad scan (ADR-002 D3) — burying the officer in failures the
scan itself caused helps nobody. But the same rule ran on the edit path, so
blanking a field *deleted* the disagreement: a `fail` PAN check vanished, the
document improved from `failed` to `attention`, and `changedCheckIds` came back
empty so the UI was not even told to redraw.

**The decision.** `FieldValueDTO.edited` already distinguishes the two cases.
An edited-and-empty field now produces `ClearedFieldCheck` — a `warn` carrying the
same check id, so it replaces the check in place and is reported as changed.
Clearing a field is a deliberate statement that the value could not be confirmed,
and it belongs on the worklist. A field nobody ever read still produces no check.

`CheckReconciliation._changed_ids` additionally reports ids that disappeared, since
a check that stopped existing has changed as surely as one that moved.

## D4 — The note declines to recommend anything until the reading is done

**The bug (High, proved three ways).** `_recommend` branched only on open items,
and "nothing is open" is indistinguishable from "nothing was looked at". A thread
with zero documents produced `Documents read: 0` directly above
`Recommendation: Fit to proceed`. The note is the artifact copied into the
permanent municipal file.

**The decision.** The recommendation reads `summary.thread_status`. A `new` or
`running` thread gets "No recommendation yet, the documents have not all been
read". ADR-007 D8's removal of the `X of Y required` denominator stands — the floor
is on the recommendation, not a reinstated denominator.

## D5 — A run that stops part way settles the document

**The bug (Medium).** Nothing owned cleanup when the SSE generator stopped early.
The document kept a mid-run stage, and `ScrutinySummary` reports `running` while
any document is not `done` — the UI spins with nothing behind it. This is the
general form of the bug ADR-006 D6 fixed for unsupported documents; the reasoning
was applied to one cause and not to the cause itself.

**The decision.** `analyze_document` wraps the pipeline in `try/finally`. On exit
without reaching `done`, the document is recorded `done` plus one `warn`
`AbandonedRunCheck` saying the run did not finish. Same shape as D6: settle the
stage, keep the reason visible. The view now also closes the sync generator
explicitly so this runs on disconnect rather than at garbage collection.

Note the `finally` only persists, never yields — a generator cannot yield while
handling `GeneratorExit`.

Observed while verifying: under uvicorn the run usually completes server-side even
after the client disconnects, so the document reaches `done` naturally and no
warning appears. The `finally` is the safety net for genuine cancellation, proved
by a unit test that closes the generator mid-run.

## D6 — One document's failure costs only that document

**The bug (Medium).** An unexpected exception in one document's generator
propagated out of `analyze_thread`, so remaining documents were never analyzed and
the closing `summary` was never sent. `unexpected_failure_event` had been written
for exactly this and was never called.

**The decision.** `_analyze_one` catches per document, reports the fault, yields
the officer-facing error event, and continues. `GeneratorExit` is re-raised
untouched so D5 still works. The stream always closes with one `summary` and one
`done`.

## D7 — A fault hidden from the officer is reported through a port

`clean-code.md` forbids logging in interactors and the quality gate enforces it, so
`_analyze_one` cannot log the exception it swallows. Swallowing it silently would
turn a bug into nothing at all.

**The decision.** `FailureReporterInterface` (abc in `adapters/`, implemented by
`LoggingFailureReporter`) is injected into `AnalyzeThreadInteractor`. Logging is
I/O, so it travels through a port, matching how `DocumentFileStoreInterface`
already works. A test asserts the swallowed exception object reaches the reporter.

## D8 — `catalog_service` is injected, not reached for

**The finding (High).** Five interactors obtained the catalog through a
method-level `get_service_adapter()` deferred import. Three proofs there was no
cycle to avoid: `ServiceAdapter` has no module-level imports at all; no app imports
`document_scrutiny`; and `CreateScrutinyThreadInteractor` already imported it at
module top and passed. The real cost was in the tests — nothing could substitute
the catalog, so four "unit" tests were silently integration tests, and ADR-001 D3's
promise that *every* interactor is testable with `create_autospec` and no I/O was
not being kept.

**The decision.** `catalog_service: CatalogServiceInterface` is a constructor
parameter on all six interactors that use it, supplied by
`api/interactor_factory.py`. This deviates from `interactors.md`'s literal
`@property` + `get_service_adapter()` prescription, on the same grounds as ADR-001
D10: `api` is the composition root and composition belongs there.
`ServiceAdapter` now has exactly one consumer, which is what a service locator is
legitimately for. The deferred imports inside `ServiceAdapter`'s own properties are
untouched — they are the Service Adapter Centralization pattern and are the reason
a cycle cannot form.

`IssuerConsultation` is now injected rather than self-constructed, which also keeps
`AnalyzeDocumentInteractor` at three collaborators plus storage.

The test fixture supplies the **real** `CatalogServiceInterface`, because the
catalog is in-memory reference data with no I/O and these tests genuinely want the
same specs production uses. The point of the change is that the choice is now
visible in the constructor rather than reached for at runtime.

## D9 — Input shape is validated before it reaches the record

`str(payload["value"])` accepted anything JSON could carry: `{"value": null}` wrote
the literal text `None` into a field and marked it as the officer's own correction;
`{"value": {"a": 1}}` wrote `{'a': 1}`, leaking Python syntax into an official
record. A 100,000-character value was accepted whole and echoed into a check detail.

Non-string values are refused with `400 FIELD_VALUE_NOT_TEXT`, and values over 256
characters with `400 FIELD_VALUE_TOO_LONG`.

## D10 — Sign-off requires something to vouch for

Confirming a document with zero fields returned `200` and incremented the confirmed
tally a reviewer reads. Sign-off means "I have read these values and they are
right" (ADR-007 D3); over an empty field set that is an assertion about nothing.
Now `400 NOTHING_TO_CONFIRM`. ADR-007 D3 handled *withdrawing* sign-off correctly
and never considered gating the granting of it.

## D11 — A document attached mid-run is still read

`analyze_thread` iterated a snapshot of the document tuple, so a document attached
while the run was in flight was never analyzed — and the stream closed with `done`
while its own summary said `running`, leaving a permanent spinner over unexamined
paper. The loop now re-reads the thread each pass, bounded by
`MAX_ANALYSIS_PASSES`, tracking which documents it has already handled.

## Accepted, not fixed

- **Concurrent streams on one thread duplicate extraction and the issuer call.**
  Final state stays consistent (last writer wins) and D1 now protects officer data,
  but the work is billed twice. Real, because browsers reconnect `EventSource`
  automatically. A per-thread analysis lock is the fix; deferred as it needs a
  concurrency primitive the in-memory store does not have, and ADR-006 D7 already
  makes the *settled* re-run free.
- **Parallel officer actions are read-then-write-whole-document with no locking.**
  Not reproducible across repeated attempts — the window is microseconds. Becomes
  real the moment a handler does I/O between read and write, which the retry path
  does. Same fix, same deferral.
- **The storage builds the initial queued `DocumentStateDTO` and calls
  `DocumentVerdict`.** `storages.md` says data access only. Moving it to
  `AddDocumentsToThreadInteractor` is correct and touches the intake path that is
  currently well covered; not worth the churn now.
- **`domain/` is not in `clean-architecture.md`'s declared per-app layer list.** It
  is load-bearing across four ADRs and is where this design keeps its judgement.
  Recorded here as a deliberate deviation so the next reviewer does not re-flag all
  17 files. `domain/analysis_events.py` is event construction rather than judgement
  and sits there only because the layer list offers nowhere better.
- **`ThreadRevision` and `IssuerConsultation` live in `interactors/` without the
  `<Action><Entity>Interactor` name.** They are shared collaborators (ADR-007 D6,
  D7), not use cases. Placing them under `interactors/` is what subjected
  `IssuerConsultation` to `interactors.md` and led to the D8 finding.
- **`DocumentStateDTO.page_image_urls` has no producer.** Kept: the Preview tab in
  task 15 is its consumer.
- **Frozen DTOs hold mutable dicts behind `Mapping` hints**, held immutable by
  defensive `dict(...)` copies at about eight call sites. `MappingProxyType` would
  make it structural; not worth churning mid-build.
- **`domain/open_check.is_open` is a module function while its siblings are
  stateless classes.** Cosmetic.

## Consequences

- 484 tests, up from 441. Every fix above is pinned by a test, and the four
  provable bugs were each re-verified over real HTTP after fixing.
- Domain and interactor layers still import no Django, no logger, no adapter
  implementation, and no storage implementation, and now contain no method-level
  deferred imports at all.
- `document.status`, `summary.thread_status` and the note's recommendation cannot
  disagree with one another.
- The mock issuer URL now follows `DI_SERVER_PORT` instead of hardcoding 8000,
  which had made every issuer check on another port read as a genuine
  unavailable-path demo.
