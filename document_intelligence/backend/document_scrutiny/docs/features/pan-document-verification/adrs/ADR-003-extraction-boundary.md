# ADR-003 — The extraction boundary

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: PRD AC1, AC2, AC10

## Context

`sale_deed_poc` states the spine this POC inherits: *the AI reads, the code judges*. Extraction is the
only place a model runs, and it has to satisfy two callers that want different things — Gemini wants a
typed schema it can fill in, and the check engine wants values keyed the way the catalog names them.
`EXTRACTION_MODE` also means two adapters must be interchangeable without the domain noticing.

## Decisions

### D1 — Pydantic is the model's wire format and stays inside the adapter

House rules require DTOs to be `@dataclass`. Gemini's structured output requires a pydantic model as its
`response_schema`. Both hold, because they describe different things:

| Layer | Shape | Lives in |
|---|---|---|
| Model response schema | pydantic `BaseModel` | `document_extraction/adapters/` |
| Boundary contract | frozen `@dataclass` | `document_extraction/dtos/` |

The pydantic model is an external service's payload format, exactly what an adapter exists to translate.
Nothing outside the adapter imports it. This is why the mock adapter needs no pydantic at all and why the
two adapters can satisfy one port.

### D2 — `PanRecordDTO` carries keyed field reads, not named attributes

`DeedRecord` names its fields (`doc_no`, `sro`, `sellers`). Mirroring that literally would give
`PanRecordDTO.name` / `.parent_name` / `.date_of_birth` / `.pan`, and then *every* adapter would need a
second translation into the catalog's field keys (`name`, `parentName`, `dob`, `pan`) before the check
engine could use it. The DTO therefore carries `Tuple[FieldReadDTO, ...]` keyed by catalog field key.
The DeedRecord-mirroring metadata that earns its place — `overall_confidence`, `low_confidence_fields`,
`boxes`, `page_count` — is kept.

The Gemini schema still has named attributes, because that is what a model can fill in; mapping them to
keys is the adapter's job, which is where the knowledge belongs.

### D3 — Overall confidence is the weakest field read

`DeedRecord` has the model self-report an overall confidence. A number the model invents about its own
certainty is not comparable between the two modes, and the mock has no model to ask. Taking the minimum
of the per-field confidences is derivable from either adapter, monotonic, and matches how an officer
reads the card: a record is only as trustworthy as its shakiest field.

### D4 — `low_confidence_fields` is derived, never asserted

`DeedRecord` lets the model list the fields it is unsure about. Deriving the list from the per-field
confidences instead makes the invariant "everything named here is genuinely below the review threshold"
true by construction rather than by trust, and it is testable with any input. The Gemini adapter maps the
model's own doubts onto per-field confidences and the same derivation runs.

### D5 — An uploaded read is discounted; a sample read is not

The prototype multiplies confidence by `0.85` for upload-sourced documents. In mock mode this is doing
real work: the canned read describes a *specimen*, so applying it to a file nobody looked at should not
claim specimen-grade certainty. The factor is `UPLOAD_CONFIDENCE_FACTOR` and the rounding is half-up to
two places, matching the prototype.

### D6 — An unrecognised `EXTRACTION_MODE` raises

The factory has no default branch. A typo in the environment fails immediately and by name rather than
silently serving mock reads to someone who asked for real extraction — which would be the worst possible
failure for a demo, because it looks like it worked.

### D7 — Classification and extraction are separate port methods

`PanExtractorInterface` has `classify_document` and `extract_pan_record`, mirroring `sale_deed_poc`'s
`inventory_file` / `extract_one` split and the prototype's `identify` / `extract` stages. Keeping them
separate is what lets the pipeline stop after classification when the type is declared-but-unimplemented
(AC10) without paying for a detailed read it would throw away.

### D8 — The model chooses from a closed list, and an unrecognised answer becomes `unknown`

`classify_document` builds its prompt from the catalog's own document types, so the model picks an id
that exists rather than inventing a label the rest of the system cannot resolve. Even so, a model can
return anything: an id the catalog does not know is mapped to `unknown` rather than raised, because a
document nobody can classify is a normal outcome (AC10), not a system fault. The prompt also tells the
model to judge from the page, not the filename — the filename is the *mock* adapter's signal, and letting
it leak into a real read would make the demo lie.

### D9 — Two confidence levels in gemini mode, both derived from what the model actually said

The model reports one overall confidence and a list of fields it doubts. It does not report a number per
field, so any per-field number is a stand-in. Rather than invent a continuous score, a field gets the
model's own overall confidence, or `UNCERTAIN_FIELD_CONFIDENCE` when the model named it as doubtful,
whichever is lower. Two honest levels beat four fabricated decimals, and D4's derivation then holds: the
doubted field is genuinely below the review threshold. The model's doubt list is matched against both the
catalog key and the schema attribute name, because a model asked for `parentName` will sometimes answer
`parent_name`.

### D10 — A malformed provenance box is dropped, not repaired

A box needs four coordinates and must name a field that was actually read. Coordinates outside 0–1000 are
clamped, since an out-of-range value is a scaling slip rather than a wrong location, but a box with the
wrong number of coordinates or an unknown label is discarded. The Preview tab then either has a usable
overlay or falls back to the synthetic card; it never renders a box pointing nowhere.

### D11 — Rendering failures happen before the model is called

A missing file, an absent `file_path`, or an unreadable extension raises `ExtractionFailed` during page
rendering, so no request and no cost reach the model. The tests assert `generate_parsed` was
`assert_not_called()` on each of those paths.

## Consequences

- The mock adapter is a true test double behind the same port, not a second path through the domain.
- 56 tests cover extraction with no API key and no network; the contract test asserts the two adapters
  produce the same `PanRecordDTO` field set from a recorded model response.
- Provenance boxes exist in both modes: canned coordinates in mock, real model coordinates in gemini,
  so the Preview tab has one contract to render.
- Verified against the live model: a synthetic PAN card classified as `pan` at 0.99, all four fields read,
  `14/08/1979` normalised to `1979-08-14`, and box coordinates that match the source image once
  de-normalised. The card's placeholder photo and absent hologram were reported as missing, which is the
  structure check doing its job rather than a mapping bug.
