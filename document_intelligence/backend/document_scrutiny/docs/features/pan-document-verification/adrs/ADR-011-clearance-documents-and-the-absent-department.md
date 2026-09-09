# ADR-011 — Clearance documents, and a department there is nothing to ask

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: the extension of AC1–AC11 to the Irrigation NOC

## Context

ADR-009 made two more identity documents real; ADR-010 made the registered
property documents real. Both reused the extraction port, the check engine and the
issuer seam unchanged, which is the outcome ADR-002's catalog-driven engine was
designed for. The Irrigation NOC is the first *clearance letter* to become real,
and it reuses all of that too — but it breaks an assumption none of the previous
types tested.

Every implemented type until now had a department to ask. The prototype
(`index.html`) marks the Irrigation NOC `service: null, manualOnly: true`: the
Irrigation and CAD Department publishes no verification interface. Flipping
`IRRIGATION_NOC_SPEC.implemented` to `True` therefore walked the pipeline into
`IssuerConsultation.consult`, which called `get_issuer_service(None)` and raised
`IssuerServiceNotFound` — a crash where a verdict belonged. That is the one
decision this pass had to make rather than copy.

## D1 — An absent department is reported as a check, not skipped

`_verify` still runs, and the verify step still emits its `running`/`done` frames.
`IssuerConsultation` branches on `document_type.issuer_service_id is None` and
returns `ManualVerificationCheck` instead of consulting anyone.

The alternative was to skip the step: no verify frames, no external check. It was
rejected because the officer would then have to notice an *absence* — a document
with no `:issuer` check among its checks — and correctly infer why. Every other
document on the same thread carries one. A missing check reads as a run that did
not finish, which is exactly the failure `settle_if_abandoned` exists to prevent
elsewhere. Reporting it says the question was reached and answered.

The check carries the same id as a real answer, `<document_id>:issuer`. So every
implemented document has exactly one external check whether or not its department
can be reached, and `CheckReconciliation._issuer_checks` (which preserves external
checks verbatim across a re-check) needs no new case: an officer's edit cannot
conjure an interface any more than it can change what a department holds
(ADR-007).

It carries **no** `issuer_call`. Nothing was sent, so there is nothing to
disclose, and the frontend's "What was asked" panel is gated on the call being
present rather than on the check's status.

## D2 — It reports `info`, so it never sits in the officer's queue

The tempting statuses are `unavailable` ("could not check") and `warn`. Both are
wrong, and for the same reason: they are *open* (`domain/open_check.py`), which
puts the item in `summary.open_items`, holds the thread in attention, and offers
the officer "I have seen this" and "Ask the applicant".

None of those is the remedy. An unreachable department is a transient fault worth
retrying — this is a permanent fact about the department, and no scan the applicant
sends will change it. An item that can never be closed by the applicant does not
belong in a shortfall, and a thread parked in attention forever teaches the officer
to ignore the state.

So it is `info`: a document carrying only this check reads `verified`, and the
thread reads `clear`. The one disposition that *does* apply — the officer verifying
the letter against the original — stays available, because `ResolveCheckInteractor`
works on any check and never rewrites the machine's verdict (ADR-007). The
frontend offers exactly that one action, via
`offersOnlyManualVerification`, rather than widening `isOpenCheck` and
re-importing the queue problem this decision exists to avoid.

The trade-off is real and is accepted here rather than hidden: a note can read
*Fit to proceed* over a document no machine confirmed. The prototype behaves the
same way, and the officer's own verification is the control — this system's
position throughout is that the officer is the decision-maker, not that every
document must be machine-verifiable before sanction.

## D3 — Retrying is refused from the catalog, not from the check's shape

`POST .../retry-verification` raises `NoIssuerToRetry` (400 `NO_ISSUER_TO_RETRY`),
distinct from `CheckNotRetryable`, which means a department that answered and
agreed. Re-asking here would run the same non-call and present it to the officer
as a fresh attempt.

The guard reads `document_type.issuer_service_id is None` from the catalog rather
than `check.issuer_call is None` from the check. Both are true today, but only the
first states the fact: whether a department can be reached at all is a property of
the document type, and a check that merely happens to be missing its call payload
is a different bug that should not be silently absorbed into this branch.

## Consequences

- The Irrigation NOC runs the full identify → extract → checks → verify pipeline
  with no new stream, no new engine, no new officer action and no new API route.
  Its checks — the applicant and survey number against the application, the
  validity window, the seal and the signature — are generated from its catalog
  entry alone, as ADR-002 intended.
- `nocNo`, `issuedBy`, `issueDate` and `bufferCondition` produce no checks: there
  is nothing on the application to compare them against and no published structure
  for a NOC number. They are read, shown and left to the officer's eye.
- Two canned reads are seeded, for the two applications declaring
  `nearWaterBody: Yes`. BN/2026/0377 carries the prototype's own clean NOC;
  BN/2026/0421 carries one that lapsed in May 2026, which exercises the validity
  rule's `lapsed` branch end to end for the first time.
- A new registry test asserts the invariant
  `document_read_registry` states in a comment: every type marked implemented has
  a read registered, and every read maps only keys its catalog entry declares. That
  is the guard that turns the next "implemented but unreadable" wiring mistake into
  a failing test rather than an officer being told a clean scan is unreadable.
- The stale "This build reads PAN only" wording in `UnsupportedTypeCheck` is
  corrected; it has been untrue since ADR-009.
