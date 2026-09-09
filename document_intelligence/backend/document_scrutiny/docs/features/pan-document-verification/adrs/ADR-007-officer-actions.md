# ADR-007 — Officer actions on a read document

Status: accepted
Date: 2026-09-08
Scope: `document_scrutiny` officer actions — field edit, sign-off, check resolution,
issuer retry, service overrides, scrutiny note.

## Context

After a run finishes, the officer is the decision-maker. The machine has read a
document, compared it against the application, and asked the Income Tax
Department for an opinion. Every one of those three can be wrong, and the officer
is the only party who can look at the original paper. The actions here are how
that authority is expressed without letting the officer's disposition masquerade
as evidence.

## D1 — An officer's disposition never rewrites the machine's verdict

`ResolveCheckInteractor` sets one of `acknowledged`, `manual` or `requested`. It
never touches `status`, `title` or `detail`.

A check marked "verified by hand" still reads `warn` with its original title, and
the demo confirms it: `check status kept: warn | manual: True | thread: clear`.
The check stops holding the thread open (`open_check.is_open` excludes `manual`
and `acknowledged`) but the record of what the machine found survives intact.

Rejected: flipping a manually-verified check to `pass`. It reads better on screen
and destroys the audit trail — a later reader could not tell a clean document from
one an officer waved through. The prototype's own re-check code had to carry
`old.status` and `old.title` forward specifically to undo that damage; not doing
it in the first place is simpler and truer.

## D2 — The issuer's answer is not derivable, so it survives a re-check

`CheckReconciliation.merge` recomputes rule and structure checks from the current
field values, then re-attaches any `external` check from the previous set
untouched.

An officer edit changes what *this system* read. It cannot change what the
department holds. Re-deriving the issuer check from the edited values would
fabricate an opinion nobody asked for; dropping it would lose an answer that cost
a real call. Refreshing it requires the officer to say so — that is D4.

## D3 — An edit withdraws the officer's earlier sign-off

Editing any field clears that field's `confirmed` flag and the document's
`confirmed` flag.

Sign-off means "I have read these values and they are right". Changing a value
makes the earlier statement about a document that no longer exists. Silently
keeping `confirmed = True` would let a document reach `verified` carrying an
assertion the officer never made about its current contents.

## D4 — A department that already agreed is not asked again

`RetryIssuerVerificationInteractor` raises `CheckNotRetryable` when the existing
external check is `pass` (`HTTP 400 CHECK_NOT_RETRYABLE`), and
`IssuerCheckMissing` when the document was never sent for verification.

Retry exists for the unavailable and disagreeing cases. Re-asking a settled
question spends a call and invites a *different* answer to something already
resolved, which the officer would then have to reconcile for no gain.

## D5 — A fresh answer arrives unresolved

When a retry returns, the replacement check carries no `acknowledged`, `manual` or
`requested` flag, even if the answer it supersedes had them.

Those flags recorded the officer's reading of *the previous answer*. Carrying them
onto a new one would hide a fresh failure behind a stale acknowledgement. Verified
by test: an acknowledged `unavailable` check retried into `not_matched` comes back
unacknowledged and the thread returns to `attention`.

Note the asymmetry with D2/`CheckReconciliation`, which *does* carry flags forward.
The difference is what moved: in a re-check the check is the same question
re-evaluated, so the officer's reading still applies; in a retry the answer itself
is new.

## D6 — Consulting the issuer is one collaborator, used by both callers

`IssuerConsultation.consult(thread=, document=, document_type=) -> CheckDTO` is
shared by `AnalyzeDocumentInteractor` and `RetryIssuerVerificationInteractor`.

Retry is not a special case of verification — it is the same conversation started
by a different actor. Two copies would drift, and the copy in the retry path is
the one nobody watches during a demo. Extracting it also took
`analyze_document_interactor.py` from 319 to 284 lines, which the Task 10 review
had flagged.

## D7 — Persisting an edit and re-reading the thread is one step

`ThreadRevision.save_document` writes the document and re-reads the thread to
recompute the summary, returning both.

Every officer action has a whole-thread consequence: correcting one name can move
the thread from `attention` to `clear`, and the officer needs to see that in the
same response rather than polling. Making it one collaborator keeps four
interactors from each remembering to re-read.

## D8 — The note reports what was read, not what was required

`ScrutinyNote` drops the prototype's `Documents: X of Y required provided` and
`Missing: ...` lines, reporting `Documents read: N` instead.

Consistent with ADR-002 D8: this POC has no required-document set, so a
"3 of 7 provided" line would be inventing a denominator. The shortfall lines are
dropped for the same reason — there is no shortfall register behind them.

## Consequences

- A reader of a cleared thread can always tell *why* it cleared: because the
  evidence agreed, or because a named officer overrode it.
- The issuer's opinion can only be changed by the issuer, on request.
- `manual` and `acknowledged` both close an item; `requested` does not, since
  asking the applicant for something does not resolve it.
- Editing a field on an unsupported document is impossible by construction: it has
  no field values, so `DocumentFieldNotFound` fires before any type lookup.
