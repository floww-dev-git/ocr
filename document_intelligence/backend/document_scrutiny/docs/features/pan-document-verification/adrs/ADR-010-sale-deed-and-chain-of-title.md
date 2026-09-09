# ADR-010 — Sale deed, bundle segmentation and chain of title

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: POC-grade property scrutiny, ported from `sale_deed_poc`

## Context

A PAN card is one page that names one person. A sale deed is different in kind: a
single uploaded PDF is often a *bundle* of several registered deeds photocopied
together, and what the officer actually needs is not a field-by-field check of one
page but whether the chain of ownership across those deeds holds — that each
seller was the previous buyer, over the same parcel, without a gap. This pass ports
the `sale_deed_poc` build: segment a bundle into its child deeds, read each,
consult the registrar (IGRS) per deed, and trace the chain of title into an
ownership report. Risk is display-only; it never stands in for the verdict.

The mechanics — segmentation, the chain engine, the four scenario bundles — are
taken as they exist in the POC. This ADR records the decisions where the port had
to differ from a naive reading, and the deviations a reviewer would otherwise
re-flag.

## D1 — The mock registrar restates the deed records; it does not import them

`mock_issuer_services` stands outside the domain and imports nothing from any
`document_*` app (ADR-004). The deed records IGRS holds are stated in full in
`igrs_deed_records.py`, not derived from `document_extraction`'s sample reads —
even though the two overlap heavily for the clean chain.

The reason is the same one ADR-004 D1 gave for PAN, sharpened by the fact that a
deed record has more fields to disagree on. A fake department that shares a data
structure with the system querying it cannot show the one thing it exists to show:
the paper and the register disagreeing. If IGRS derived its answer from the same
read the officer is checking, the registrar would agree with every misread deed by
construction. Restating the record is what lets a differently transliterated buyer,
or a vendor who never bought, be caught by consulting the register.

Rejected: a shared fixture imported by both. It removes duplication at the cost of
the one property that makes the mock honest.

## D2 — The four bundles are alternate histories over three shared registration numbers

The scenario bundles (`01_clean_chain`, `02_weak_transliteration`,
`03_gap_extent_overflow`, `04_broken_stranger_seller`) are written over the same
parcel — Sy. No. 142/2, Plot 17, Kondapur — reusing three registration numbers
(`1188/2003`, `2451/2011`, `5820/2019`). A register holds exactly one history per
registration number, so IGRS is seeded with the clean chain only.

The consequence, recorded so it is not mistaken for a bug: when bundle 02's
weakly-transliterated 2011 deed is sent to IGRS, the registrar answers about the
*clean* 2451/2011 it holds, and reports a name partial-match — a **fixture
artefact**, not the finding the scenario is about. The transliteration story bundle
02 exists to prove is graded by the **chain engine** (which scores the buyer→seller
handover as a `weak` link), not by IGRS. The per-deed issuer check and the chain
verdict are answering different questions here; the chain verdict is the one the
scenario is designed around.

The alternative — a distinct registration number per scenario so IGRS could carry
each bundle's own history — was rejected as more fixture than the POC needs. The
shared-parcel design is what makes the four bundles legible as *variations on one
story*, and the chain engine is the correct grader for the variations.

## D3 — Only the current deed is compared to the applicant; only the chain links the priors

A bundle's prior deeds name prior owners. Comparing a 2003 vendor to the current
applicant would ask the officer why they differ — noise. So only the deed being
relied on (the most recent sale deed) is read as the current deed and compared to
the application; the link documents are read for the chain but not measured against
the applicant. The break a per-document check cannot see — a vendor who was never a
buyer in the chain — surfaces only when the chain is traced, which is the whole
point of tracing it.

## D4 — An officer's correction reaches the deed record, so the chain re-traces on it

Recorded in full in ADR-007's lineage and the Task 9 work: an edit to a flat deed
field (`vendor`, `extent`, …) is carried into the nested `DeedRecordDTO` the chain
reasons over, via `DeedRecordEdit`. The map from flat field to record path is
restated in `deed_edit_constants.py` rather than read off the extraction spec — how
a correction flows into the record scrutiny reasons over is scrutiny's business,
not the extractor's — and a drift-guard test pins every entry against the read spec
so the two cannot silently diverge. An edit never fabricates a party the paper did
not carry: correcting a vendor on a deed read with zero sellers changes nothing.

## Deviations recorded

Three deviations a reviewer would otherwise re-flag:

- **`lapseIsInfo` is not implemented.** The validity-window work (driving licence
  expiry) left room for a per-type "a lapse is informational, not a failure" flag.
  Only building_permit would need it, and building_permit is unsupported, so the
  flag would be dead code. Left out; noted here so its absence reads as a decision.
- **`inventory_file` is not a port method.** Segmentation does not add a
  `read_inventory`-style method to the extraction port. A bundle is reported
  through `DocumentClassificationDTO.segments` plus an `is_bundle` flag on the
  existing classification path, so the port stays type-neutral (ADR-003's boundary)
  and segmentation is a property of the read rather than a new verb.
- **Chain judgement lives in `domain/chain_of_title/`.** ADR-008 already recorded
  that `domain/` is where this design keeps its judgement despite not being in
  `clean-architecture.md`'s declared layer list. The chain engine is the largest
  instance; it is here for the same reason and should not be re-flagged.

## Consequences

- One upload of a bundle becomes the file itself (closed off with a note of what
  was found, never sent to the registrar) plus one row per registered deed, each
  read and checked in its own right, with the chain traced across them into an
  ownership report carried on a `chain` SSE frame.
- The four scenarios trace to the verdicts they were built to produce (intact,
  review, review, broken), graded over real thread state after the real reading
  pipeline — not just over the fixtures.
- A PAN-only thread emits no `chain` frame: there is no title to trace, so the
  officer is told nothing about one.
- Risk is display-only throughout: it is shown beside the verdict, never in place
  of it.
