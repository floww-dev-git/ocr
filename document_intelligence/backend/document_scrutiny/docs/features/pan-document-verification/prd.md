# PAN Document Verification — PRD

## Problem

A municipal building-permission officer receives an applicant's supporting documents as scanned
PDFs and phone photographs. Today the officer reads each one by eye and compares it, field by
field, against what the application form claims. The comparison is slow, inconsistent between
officers, and leaves no record of what was checked.

`index.html` prototypes the answer as client-side theatre. This feature makes the first slice of
it real: the officer attaches a PAN card, the system reads it, and deterministic checks report
where the document and the application disagree.

## Users

| User | Need |
|---|---|
| Scrutiny officer | See what each document says, where it disagrees with the application, and record a decision on every disagreement |
| Applicant (indirect) | Not be asked to resubmit documents that were already correct |

## Scope — this pass

- One document type: **PAN**. Eleven further types are declared in the catalog and reported as
  recognised-but-unsupported when they arrive.
- Three seeded applications, kept verbatim from the prototype, including `BN/2026/0377` whose PAN
  reads `MOHAMMED IRFAN SIDDIQI` against an application saying `Mohammed Irfan Siddiqui`.
- Real extraction by default; a mock extractor for offline demos and tests.
- The Income Tax PAN verification service is mocked behind a real HTTP call.

## Scope — extension: identity documents and sale deeds

A later pass made three more document types real, reusing the extraction port, the check engine,
the issuer seam and the analysis stream unchanged. Voter ID stays unsupported by the applicant's
instruction.

- **Aadhaar**, verified against a mocked **UIDAI** demographic-authentication service.
- **Driving licence**, verified against a mocked **Sarathi** service, including a validity window.
- **Sale deed**, ported from `sale_deed_poc`: a single uploaded PDF is segmented into the registered
  deeds it bundles together, each is read and checked, the registrar (**IGRS**) is consulted per
  deed, and the **chain of title** across the deeds is traced into an ownership report. A fourth
  seeded application, `BN/2026/0455` (Prakash Iyer, Sy. No. 142/2 Plot 17 Kondapur, 400 sq.yd),
  carries the four scenario bundles.
- **Risk** on the ownership report is display-only. It is shown beside the verdict, never in place
  of it.

The reasoning for the two decisions that departed from a naive reading — Aadhaar checked for
structure rather than its Verhoeff checksum, and the per-demographic answer shape — is in ADR-009.
The sale-deed decisions, the shared-parcel scenario design, and the recorded deviations
(`lapseIsInfo`, `inventory_file`) are in ADR-010.

## Out of scope — this pass

Thread history and search, the required-document checklist, shortfall tracking, conversational
Q&A, cross-document checks, reclassifying a document to another type, and durable persistence.

## Behaviour

1. The officer picks an application and attaches a PAN card.
2. The system reports four stages as they happen: identify, extract, checks, verify.
3. Each read field carries a confidence and is editable.
4. Checks compare the read fields against the application and against the PAN's own format,
   then the issuer's record is consulted.
5. Editing a field re-runs every check.
6. Every disagreement is either resolved by an edit, acknowledged, or marked verified by hand.
7. The officer copies out a scrutiny note recording what was checked and what remains open.

## Acceptance criteria

| # | Criterion |
|---|---|
| AC1 | A PAN whose fields all agree with the application reports every check passing and a `clear` thread |
| AC2 | A PAN whose name differs by one character reports a name warning, not a pass and not a failure |
| AC3 | A PAN whose number does not match the application reports a failing check |
| AC4 | A PAN whose number is not a structurally valid PAN reports a failing format check, with no application context needed |
| AC5 | A structural element the template expects but the document lacks reports a warning |
| AC6 | The issuer's record disagreeing with the read name reports a warning, and the disclosed payload agrees with the verdict shown |
| AC7 | The issuer not responding reports the check unavailable, never a pass and never a crash |
| AC8 | Editing a field re-runs every check and the document and thread verdicts follow |
| AC9 | An acknowledged warning stops counting as open; the thread can reach `clear` without the underlying value changing |
| AC10 | A document type other than PAN is reported as recognised-but-unsupported rather than silently read as PAN |
| AC11 | The scrutiny note lists every open item and flips its recommendation once nothing is open |

## Non-functional

- Deterministic offline demo path (`EXTRACTION_MODE=mock`) with no API key and no network.
- The verdict engine is testable with no server, no database, and no API key.
- Local single-user POC: no authentication, in-memory state, files under `uploads/`.
