# ADR-001 — Clean Architecture boundaries for the Document Intelligence POC

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: PRD AC1–AC11

## Context

`index.html` prototypes the whole product in one file: reference data, judgement, and rendering
share a global namespace. `sale_deed_poc` proves a cleaner split for one document type with its
stated spine — *the AI reads, the code judges*. This POC has to hold both: the prototype's breadth
(twelve document types, three applications, an officer-in-the-loop review cycle) and the sibling
POC's discipline, under the house standards in `.claude/rules/`.

The prototype's own structure is the strongest signal available. `DI.engine` is a pure function of
`(documents, application)` with no I/O; `DI.SAMPLE_SETS` is reference data; `DI.preview`/`DI.ui` are
rendering. That is already the layering the house rules ask for, so the port preserves it rather
than inventing a new arrangement.

## Decisions

### D1 — Six apps, with `document_scrutiny` as the only consumer

| App | Owns |
|---|---|
| `document_catalog` | What a document type is, what an application looks like — closed reference data |
| `document_extraction` | Turning file bytes into a read record. The AI lives here and nowhere else |
| `document_verification` | Talking to issuer registries |
| `mock_issuer_services` | The fake external world, standing where real government APIs will |
| `document_scrutiny` | Judgement, thread state, and the officer's review cycle |
| `api` | HTTP transport. No decisions |

`document_scrutiny` consumes the other three domain apps through their `app_interfaces/` via
deferred-import adapters. Every arrow points from the less stable app to the more stable one, so
there are no cycles and no engine-defines-ports inversion is needed: the scrutiny app is the
consumer, not a mechanism others plug into.

### D2 — DTOs returned by an `app_interfaces/` method are part of that app's public contract

App isolation forbids importing another app's internals. It cannot forbid the types its public
interface returns, or the interface would be unusable. So `document_catalog.dtos` is public *by
virtue of appearing in `document_catalog.app_interfaces`*, while its `storages`, `storage_interfaces`,
and `constants` stay private. Consumers import the interface to call it and the DTO only to type-hint
the result.

### D3 — In-memory storages behind `abc.ABC` interfaces

The POC keeps no database. Storage interfaces still exist, and the in-memory classes implement them.
This is not ceremony: it is the only thing that makes the later ORM swap an implementation change
rather than an interactor rewrite, and it lets every interactor be tested with `create_autospec` and
no I/O at all.

### D4 — Application field values are all strings

The prototype mixes types in one map (`extentSqYd: 267`, `heightM: 16.5`, `applicantName: '...'`).
Modelling that as `Union[str, int, float]` would push type-narrowing into every consumer for no gain,
since the UI renders them as text and the comparison rules parse what they need — exactly as the
prototype's own `Number(...)` and `parseExtent` do. `ApplicationDTO.field_values` is therefore
`Mapping[str, str]`, stringified once at the reference-data boundary.

### D5 — A field's special comparison rule is one optional enum, not four booleans

The prototype flags fields with `addressCheck`, `validity`, `extentCheck`, `heightAtLeast`. Inspecting
all twelve types shows a field never carries more than one of them, so `FieldSpecDTO.comparison_rule`
holds at most one `FieldComparisonRule` value. Four independent booleans would imply combinations the
domain does not have.

### D6 — The catalog raises on an unknown id rather than returning `Optional`

House storage guidance prefers `Optional[DTO]` for single lookups, which fits a database row that may
legitimately be absent. The catalog is a closed set fixed at build time: an unknown document type id
is a caller defect, not a missing record. `get_document_type` and friends raise a domain exception
carrying the offending id, which is boundary translation, not business logic.

### D7 — The issuer check derives its status from the issuer's own payload

The prototype's `BN/2026/0377` sample sets the service outcome to `pass` while its response body
carries `nameMatch: false`. Rendered faithfully, the card would claim the issuer confirmed the
document while displaying the payload that contradicts it. The check therefore reads the response:
`nameMatch: false` maps to **warn**. This is a deliberate divergence from the prototype's data —
an officer must never be shown a verdict its own evidence disputes.

### D8 — A PAN format rule is added, and it lives in the domain layer

The prototype validates the PAN only by comparing it to the application. A PAN has a defined shape —
five letters, four digits, a letter, with the fourth character encoding holder type — so a malformed
number is knowable with no application context at all. `PanFormat` is a domain value object beside
`NameSimilarity`; this is the check that still works when there is nothing to compare against.

**The three states are one field, not a combination of flags.** Inspecting a PAN yields exactly three
outcomes, and they carry different verdicts:

| `PanFormatState` | Meaning | Check verdict |
|---|---|---|
| `MALFORMED` | Blank, wrong length, or breaks the letter/digit pattern | **fail** (AC4) |
| `UNRECOGNISED_HOLDER_TYPE` | Shape is right, the fourth character is not an issued holder-type code | **warn** |
| `RECOGNISED` | Shape is right and the holder type is known | **pass** |

An earlier draft expressed this as `well_formed: bool` alongside an optional label, which meant
`holder_type_label is None` spanned both the fail row and the warn row — a caller branching on the
label alone would silently downgrade a malformed PAN to a warning. `PanFormatDTO.state` is therefore
the single field a caller branches on; the other fields are detail for the check's message.

**Lowercase is rejected, surrounding whitespace is not.** A PAN printed in lowercase is a bad read
worth surfacing; leading or trailing whitespace is transport noise from extraction. The comparison
rule that matches the read PAN against the application is separately lenient (it strips and uppercases
both sides, as the prototype does) because there the question is "same number?", not "valid number?".

### D9 — REST + SSE, no GraphQL

House rules assume Graphene. The four-stage analysis reveal is a server-push stream; GraphQL over
HTTP cannot stream, and subscriptions would mean websockets for one progress feed. The transport is
REST with one SSE endpoint, matching `sale_deed_poc`. Approved deviation.

### D10 — `api` is the composition root, and may reach into the domain apps

App isolation binds peer domain apps to each other's `app_interfaces/`. It does not bind the
transport layer, which has to instantiate something concrete or nothing runs. House guidance puts
this wiring at the resolver ("resolvers already instantiate storages"); here the equivalent seat is
`api/views/`. So `api` imports interactors, storages, and presenters directly and assembles them,
while carrying no decision of its own. A domain app doing the same to a peer would be a violation;
the composition root doing it is the pattern.

### D11 — `uv`, not `pip` + `virtualenv`

The root `CLAUDE.md` bootstrap belongs to the `sales_crm_backend` project, which is not in this
repository. `sale_deed_poc` uses `uv`, and this POC sits beside it. Approved deviation.

## Consequences

- The verdict engine is testable with no server, no database, and no API key — the highest-value
  behaviour has the cheapest test.
- Adding Aadhaar means a catalog entry, an extractor prompt, and rule registrations. No app moves.
- `EXTRACTION_MODE` selects an adapter behind one interface, so the mock is a true test double
  rather than a second code path through the domain.
- Two divergences from the prototype are load-bearing and recorded here: D7 and D8.
