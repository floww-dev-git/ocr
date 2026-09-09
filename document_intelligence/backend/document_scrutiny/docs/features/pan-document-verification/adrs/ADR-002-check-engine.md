# ADR-002 — The check engine

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: PRD AC1–AC5, AC8, AC9

## Context

The prototype's `E.ruleChecks`, `E.summary`, `E.docStatus` and `E.threadStatus` (index.html:1006–1090)
decide every verdict the officer sees. They are pure functions of `(documents, application)` with no
I/O, which is what makes the whole product testable. This ADR records how that survives the port into
Clean Architecture.

## Decisions

### D1 — Judgement is a domain calculator; the interactor only composes

`RunDocumentChecksInteractor` holds no storage and performs no I/O. It reads a request DTO and delegates
to four domain units, each owning one rule family:

| Unit | Owns |
|---|---|
| `FieldComparisonChecks` | read value vs application value, one comparator per application field key |
| `PanFormatCheck` | the PAN's own structure, needing no application context |
| `StructureChecks` | whether a template element was detected |
| `DocumentVerdict` / `ScrutinySummary` | rolling checks up to a document and a thread status |

Rollups live in `domain/`, not in an interactor, because three separate use cases need them — analyze,
field update, and the scrutiny note. An interactor apiece would have duplicated them.

### D2 — The checks interactor is handed its document type and application, not their ids

It could take ids and resolve them through the catalog adapter. Instead the caller resolves both once
and passes the DTOs. The analyze flow already holds them, and a re-check after every field edit would
otherwise re-read reference data that cannot have changed. The interactor therefore needs no adapter at
all, which is why it can be tested with no mocks whatsoever.

### D3 — An unread field produces no check

The prototype skips a field whose value is empty (`if (v == null || v === '') continue;`). The port keeps
this, and it extends to the PAN format rule: a blank PAN yields no format check rather than a failing one.
An officer looking at a document that could not be read needs "nothing was read here", not a wall of
failures blaming the applicant for a bad scan. `PanFormat` still handles a blank input, so the domain
object stays complete for callers that do want that answer.

### D4 — A structure element only warns on an explicit negative

`structure_findings.get(key) is not False` — an absent key means "not looked for", which is not a finding.
This mirrors the prototype's `doc.structure[s.key] !== false` and matters because extraction reports only
what it inspected.

### D5 — The identifier match is whitespace-and-case lenient, and nothing more

`_normalise_identifier` strips whitespace and uppercases, exactly as the prototype does. It deliberately
does **not** strip punctuation: `DQRPK-4831L` is a different number, not noise. Together with ADR-001 D8's
strict format rule this produces a deliberate, tested asymmetry — `dqrpk4831l` matches the application
(same number) while failing its format check (not a validly written PAN).

### D6 — `document_scrutiny` restates the application field keys it can compare

App isolation forbids importing `document_catalog.constants`. `ComparableApplicationField` therefore
repeats four string values that `document_catalog` also declares. The duplication is deliberate and is
pinned by a contract test asserting every comparable key appears in the catalog's published PAN spec, so
the two sides cannot drift silently.

### D7 — Asking the applicant does not close a finding

`is_open` treats a check as resolved when it is `acknowledged` or `manual`, never when it is `requested`.
Raising a shortfall means the disagreement is still real and still awaiting an answer; the prototype's
`isOpen` agrees.

### D8 — The required-document checklist is out of this slice, so the summary has no `missing`

The prototype's `E.summary` reports `provided` / `required` / `missing` from `E.requiredDocs`, which is
driven by rules about building height and proximity to water bodies — a feature deferred with the rest of
the checklist. `ScrutinySummaryDTO` therefore carries no `missing` field and `thread_status` is `attention`
purely on open items. Adding it later is additive: a new input to `ScrutinySummary.summarise` and one more
term in the thread-status decision.

## Consequences

- The engine needed 42 tests and zero mocks. No server, no database, no API key.
- `CheckDTO` already carries `issuer_call`, so the external check in Slice 4 adds a value, not a shape change.
- `CheckGroup.CROSS` exists and is unused until a second document type lands, which is the point.
