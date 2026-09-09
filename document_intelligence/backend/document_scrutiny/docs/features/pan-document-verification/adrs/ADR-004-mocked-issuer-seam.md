# ADR-004 — The mocked issuer seam

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: PRD AC6, AC7

## Context

No public Income Tax Department PAN verification API is available to this POC, so the issuer has to be
simulated. The prototype simulated it by hardcoding the answer, including a literal `nameMatch: false`
for one seeded application. That is enough for a click-through, but it means the seam where a real
integration lands has no shape: no request, no credential, no failure modes.

`mock_issuer_services` is therefore a Django app that stands *outside* the domain and occupies that seam.
It imports nothing from any `document_*` app, which is the property that makes it honest — the external
world does not share our reference data.

## Decisions

### D1 — The mock holds the department's record and computes the match

Rather than replaying a canned `nameMatch`, each `ItdPanRecord` carries the name and date of birth the
department holds, and the endpoint compares what was submitted against them. `BN/2026/0377` reports
`nameMatch: false` because `MOHAMMED IRFAN SIDDIQI` genuinely differs from the registered
`MOHAMMED IRFAN SIDDIQUI` — and it keeps reporting it after an officer edits the field, which a canned
flag could not.

### D2 — A demographic field that was not submitted is rejected, or reported as `null`

The first draft made missing input indistinguishable from disagreement: a request carrying only a PAN
came back `nameMatch: false`, which the check would have shown as a warning identical to a real issuer
disagreement. `name` is now mandatory and its absence is a `400 NAME_REQUIRED`. `dob` is optional, and
when it is absent `dobMatch` is `null` — never `false`. This matters because AC6 requires the disclosed
payload to agree with the verdict shown: a `pass` card carrying `dobMatch: false` for a date nobody
submitted would be exactly the contradiction ADR-001 D7 exists to prevent.

### D3 — The department normalises noise, but does not fuzzy-match

`_normalise_name` uppercases, replaces non-alphanumerics with spaces, and collapses whitespace. So a
trailing period or a stray comma in a real Gemini read does not flip the issuer's answer while our own
name check scores 100% — a divergence that would have looked like a bug.

It deliberately stops there. `S RAO KANDULA` does **not** match a registered `SRINIVAS RAO KANDULA`,
even though `NameSimilarity` scores that pair 1.0 through its initial-abbreviation rule. Tolerating an
abbreviation is our side's judgement about a plausible read; the department either holds the name or it
does not. Keeping the two rules different is the point of consulting the issuer at all — an independent
opinion that always agreed with us would be worth nothing.

### D4 — Dates are compared after normalisation, not as strings

A PAN card prints `dd/mm/yyyy`, the officer's screen shows `dd-mm-yyyy`, and the extraction contract is
ISO. All three are accepted and normalised before comparison, so a date that agrees cannot be reported
as a mismatch because of the format it arrived in.

### D5 — The seam carries a credential

`X-Api-Key` is required and a missing or wrong key answers `401` with a named error code. The key itself
is a POC constant. The value is not the point: without it the adapter written against this mock would
grow no place to read a credential from settings and no branch mapping an authentication rejection, and
both would have to be retrofitted when a real integration arrives.

### D6 — Unavailability is demonstrable two ways

`timeout` waits the caller's budget **plus** a margin, both read at call time, so raising
`ITD_REQUEST_TIMEOUT_SECONDS` at runtime cannot leave the mock answering inside it. `server_error`
returns `503`. AC7 needs the adapter's unavailable path to be exercised by something other than a clock,
and a transport error is a different code path from a timeout.

### D7 — `status` alone decides the verdict

The response carries no `found` flag. It was derivable from `status` in every path and actively wrong in
one — a forced failure for a PAN the department does not hold reported `found: true`. The four verdicts
the check needs are distinguishable on `status`, with `nameMatch` refining `VALID` into pass or warn, and
`nameMatch`/`dobMatch` are explicitly `null` (never absent) on `NOT_FOUND` and `N`, so an adapter reaching
for them cannot read "not applicable" as "mismatch".

### D8 — The reference identifies the transaction, not the subject

`referenceId` is a fresh opaque value per call. An earlier draft derived it from the PAN, which meant the
reference an officer copies into a scrutiny note both repeated across calls and carried the PAN into the
note.

### D9 — The demo override is gated on `DEBUG`

`X-Demo-Outcome` is how the Demo menu forces pass / fail / timeout / server error. Any caller who can
reach the endpoint can use it, so it is refused with `DEMO_OUTCOME_NOT_PERMITTED` when `DEBUG` is off.
An absent header always means `auto`; an unrecognised value is rejected rather than ignored.

## Open questions for a real integration

Two things this mock asserts that only a provider specification can settle. Both are contained: the
response-to-check mapping lives in one adapter, so either is a single-file change.

- **The status vocabulary.** `VALID` and `N` come from the prototype; `NOT_FOUND` is this POC's own. In
  some real vocabularies `N` already means "not in the database", which is what `NOT_FOUND` means here —
  in which case the adapter's `NOT_FOUND` branch would be dead and `N` would carry both meanings.
- **Whether the registered name comes back.** This mock withholds it, and a test asserts it never appears
  in the response. Some verification tiers do return the name on record. If the real one does, an officer
  resolving `nameMatch: false` gains something concrete to resolve against, and both the payload and the
  card would want a place to show it.

## Consequences

- 50 tests cover the endpoint, including every rejection path and all five demo outcomes.
- The seeded demo outcomes now fall out of a mechanism rather than a fixture, and the drift risk is
  one-directional: a noisy read can only produce *more* warnings, never a false pass.
- Task 8's adapter has a credential to send, a timeout to hit, a `503` to map, and a malformed-PAN
  rejection to distinguish from an unknown holder.
