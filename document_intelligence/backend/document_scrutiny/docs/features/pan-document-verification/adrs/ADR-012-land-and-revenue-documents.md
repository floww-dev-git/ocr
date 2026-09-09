# ADR-012 — Land and revenue documents, and an EC downgraded to manual-only

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: the extension of AC1–AC11 to five property/land documents

## Context

ADR-011 made the Irrigation NOC real and, with it, the first document type whose
issuing department publishes no verification interface — settled through
`ManualVerificationCheck` rather than a department call. This pass adds five more
documents from the property/land scrutiny set, all of them the same shape:

1. **Encumbrance certificate (EC)** — already declared (`ec`), was
   `implemented=False` against IGRS.
2. **Land conversion certificate** (`conversion_cert`, new) — RDO, Telangana NALA
   Act 2006.
3. **Market value certificate** (`market_value_cert`, new) — sub-registrar
   valuation.
4. **Pattadar pass book / title deed** (`pattadar_passbook`, new) — Revenue
   Department (Dharani).
5. **Occupancy rights certificate** (`orc`, new) — RDO, for Inam lands.

None of the five is verified against a live department in this build. They are read,
compared against the application form, and left for the officer to confirm by hand.
Everything that made that possible already existed after ADR-011; this pass is
almost entirely catalog data plus read modules, with no new engine, stream, officer
action or API route.

## D1 — All five are manual-only, reusing the ADR-011 path unchanged

Each spec carries `issuer_service_id=None`, so `IssuerConsultation` returns a
`ManualVerificationCheck` (info, no issuer call), retry is refused with
`NoIssuerToRetry` / `NO_ISSUER_TO_RETRY`, and the frontend offers only "Verified by
hand" via `offersOnlyManualVerification`. No code in the scrutiny, verification or
API layers changed for this — the five are entirely expressed as catalog specs,
Gemini read modules and canned sample reads, exactly as ADR-002's catalog-driven
engine intends.

## D2 — The EC is deliberately downgraded from IGRS to manual-only, for now

The EC was declared against `IssuerServiceEnum.IGRS` with `implemented=False`. There
is a working IGRS mock (it verifies registered deeds), so wiring the EC to verify
against it was possible. This pass does **not** do that: it flips the EC to
`implemented=True` and sets `issuer_service_id=None`, shipping it read-and-checked
and manual-only, consistent with the other four land documents.

This is a downgrade from what the catalog *declared*, and it is recorded here rather
than made silently. The reason is scope and honesty: an EC is not a registered deed,
and the IGRS deed-lookup mock answers about deeds, not about the encumbrance history
a real EC verification would need. Pointing the EC at that mock would produce a green
"IGRS confirmed" that means nothing about the encumbrances. Manual-only tells the
truth — the officer reads the encumbrance list themselves — until a real EC lookup
exists, at which point re-wiring is a one-line spec change plus an answer reader,
the same seam ADR-005 describes.

## D3 — The field lists for the four new types are inferred, not from specimens

The EC's fields were already declared. The fields for the conversion certificate,
market value certificate, pattadar pass book and ORC are inferred from the general
Telangana forms — conversion order number and NALA assessment; certificate number
and market value per sq. yd; pass book / khata number, pattadar and land
classification; ORC number, occupant and Inam category. They are internally
consistent, and the read modules, the sample reads and the catalog specs all agree
on the keys, so a mock run and a real run emit the same fields. But they are not
transcribed from real documents, and a real integration is where the exact fields
and their labels get confirmed or corrected. This is the same standard of honesty
ADR-009 applied to the Aadhaar checksum.

## D4 — Which fields are compared, and one seeded discrepancy

Comparisons are generated from each spec's `application_field_key` links, so no
comparison code was written. The comparisons are:

- **EC**: owner→applicant name, survey number.
- **Conversion certificate**: applicant→applicant name, survey number, village,
  extent (extent-tolerance rule).
- **Market value certificate**: survey number, village. The rate per sq. yd has no
  counterpart on the application form, so it is read and shown but never compared.
- **Pattadar pass book**: pattadar→applicant name, survey number, village, extent.
- **ORC**: occupant→applicant name, survey number, village. Its extent is read for
  the record but not compared — the ORC establishes occupancy, and the decision was
  survey + village + occupant.

None of the five carries a validity/expiry check: an EC and a market value
certificate are "as-on-date" documents, and the conversion order, pass book and ORC
are standing records. The issue date is read but not range-checked.

The mock data seeds all five on BN/2026/0377 (the near-water-body application). Four
read clean and consistent with the form; the **pattadar pass book reads 390 sq. yd
against the application's 420**. That is outside the 0.5 sq. yd tolerance and is not
a rounding artefact, so the extent check warns (a WARN, not a FAIL, per
`DISAGREEMENT_STATUS_BY_APPLICATION_FIELD` — a revenue-vs-application extent gap is
something an officer can often explain). It is the demo's one caught discrepancy
among the five, and it exercises the extent-tolerance rule end to end for a
non-deed document for the first time.

## D5 — A filename-keyword collision worth recording

Classification in mock mode is by filename keyword, first match wins. "occupancy"
contains "pan" ("occu-**pan**-cy"), so an ORC filename would have routed to PAN
under the old ordering. The land-record keywords were therefore moved ahead of the
identity keywords in `filename_keyword_specs.py`, and the reason is noted in the
file. This only affects the offline mock classifier; Gemini classification is by
content against the catalog and is unaffected.

## Consequences

- Eleven document types are now implemented; the catalog declares sixteen. All five
  new/changed types run the full identify → extract → checks → verify pipeline with
  no new stream, engine, officer action or API route.
- The parametrised `test_document_read_registry.py` now guards all eleven: any
  implemented type missing a read, or a read mapping a key its catalog entry does
  not declare, fails a test rather than reaching an officer as an unreadable scan.
- The EC's move to manual-only is a deliberate, reversible "for now"; the IGRS seam
  is untouched and available.
- The four new documents' fields are inferred and marked as such; correcting them
  against real specimens is a spec-and-read edit with no engine impact.
