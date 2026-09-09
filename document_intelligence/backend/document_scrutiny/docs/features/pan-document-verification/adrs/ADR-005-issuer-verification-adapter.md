# ADR-005 — Consulting the issuer, and turning its answer into a check

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: PRD AC1, AC6, AC7

## Context

The prototype's `E.serviceResult` produced the external check by reading a canned outcome off the sample
and formatting a sentence. Two apps now sit where that one function was: `document_verification` talks to
the issuer, and `document_scrutiny` decides what its answer means. This ADR records why the line is drawn
there and how a failure to reach the issuer is represented.

## Decisions

### D1 — The verification interactor returns facts, not a check

The plan had `VerifyPanWithIssuerInteractor` returning a `CheckDTO`. It cannot: `CheckDTO` belongs to
`document_scrutiny`, and a peer app building one would be reaching across a boundary to author another
app's domain object. So `document_verification` returns `IssuerAnswerDTO` — what the issuer said,
normalised — and `document_scrutiny.domain.IssuerCheck` turns that into a `CheckDTO`.

The split also puts each piece where its knowledge lives. Only the verification app knows that a `503` and
a read timeout are both "we did not get an answer". Only the scrutiny app knows that not getting an answer
is `unavailable` rather than a failure, and that the officer should be told to verify against the original.

### D2 — One `outcome` field with five values, never a combination of flags

`IssuerAnswerDTO.outcome` is the single field a caller branches on:

| Outcome | Meaning | Check status |
|---|---|---|
| `confirmed` | The department holds the PAN and agrees on everything submitted | pass |
| `partial_match` | It holds the PAN but disagrees on a named demographic | **warn** |
| `not_matched` | It rejected the demographics outright | fail |
| `no_record` | It has no record of this PAN | fail |
| `unreachable` | We did not get a usable answer | unavailable |

`partial_match` is the divergence ADR-001 D7 called for, now reached by a mechanism: the reader compares
`nameMatch` and `dobMatch` against the payload and names the fields that disagree, so the warning sentence
and the disclosed evidence cannot contradict each other (AC6).

`dobMatch: null` means the question was not asked and is **not** a disagreement — only an explicit `false`
counts. `nameMatch` is the reverse: anything other than an explicit `true` counts as disagreement, because
a name the department did not affirm is not a name the department confirmed.

### D3 — Being unable to reach the issuer is a value, not an exception

`verify_pan` never raises for a transport problem. A timeout, a refused connection, a `401`, a `4xx`, a
`5xx`, and an unparseable body all return `outcome=unreachable` with a distinguishing
`unreachable_reason`. The reason exists so the officer is told what actually happened —
"the department reported a problem at its end" is actionable in a way "no response" is not.

An exception here would have to be caught by the analyze stream and converted anyway, and along the way
the natural failure mode would be an aborted stream rather than a document carrying an honest
`unavailable` check.

### D4 — An outcome this app does not recognise degrades to `unavailable`

`IssuerCheck` maps a vocabulary it knows. Anything else becomes `unavailable`, never `pass`. If the issuer
protocol grows a value — which ADR-004's open questions say it might — the officer sees "did not respond"
and reaches for the original, rather than being shown a confirmation nobody granted.

### D5 — The credential travels in a header and never in the disclosed payload

`request_payload` on the check carries the JSON body only: `pan`, `name`, and `dob` when it was read. The
API key goes in `X-Api-Key` and is asserted absent from the disclosure, because that payload is rendered
into the officer's Checks tab and copied into scrutiny notes.

### D6 — All three demographics are submitted

The prototype's request builder sent the PAN and, conditionally, the name — never the date of birth. That
is what would have produced `dobMatch: false` beside a `pass` (ADR-004 D2). The adapter sends every
demographic the card actually yielded, and omits `dob` entirely rather than sending an empty string when
extraction did not read one.

### D7 — Tests drive a real `httpx` client through `MockTransport`

The adapter takes an optional `transport`, so tests exercise the genuine client, request building, and
exception classes — a handler that raises `httpx.ReadTimeout` proves the real `except httpx.TimeoutException`
branch, rather than a stub standing in for it. `TimeoutException` is caught before `RequestError` because
it is a subclass of it.

### D8 — `document_scrutiny` restates the issuer vocabulary

App isolation forbids importing `document_verification.constants`, so the outcome names, the unreachable
reasons, and the disagreeing-field keys are declared again in `document_scrutiny.constants`. A contract
test pins all three sets against the verification app's enums, and pins `IssuerAnswerFactsDTO`'s fields
against `IssuerAnswerDTO`'s, so the duplication cannot drift unnoticed.

## Consequences

- 46 tests cover verification with no server and no network.
- Verified end to end against the running mock issuer: all six outcomes, including a genuine client-side
  timeout — the mock slept 4 s, `httpx` gave up at its 3 s budget, and the check reported `unavailable`
  after 3059 ms.
- The seeded mismatch reports **warn** with `nameMatch: false` visible in the same panel, so the verdict
  and its evidence agree.
