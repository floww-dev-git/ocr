# ADR-013 — The Aadhaar capability showcase

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: demonstrating the *range* of Aadhaar verification, not one check repeated

## Context

The build had grown to sixteen document types, but a demo of it showed the same
shape each time: identify, read, compare, verify. That understates what the platform
can do to a document. This pass makes the Aadhaar the worked example of the full
range — identification, field extraction with provenance, an intrinsic checksum, a
QR-vs-print integrity check, a scan-quality judgement, cross-checks against the
application, and issuer verification — each visible as a real check firing, on real
extraction, against documents engineered to trip exactly one capability.

Everything here is scoped to Aadhaar. The same scenario-gallery pattern is meant to
repeat for other types later.

## D1 — One application, many specimens

A single showcase application, **BN/2026/0601 (Rithika Sharma)**, holds the
applicant's true declared identity — including a Verhoeff-valid Aadhaar number that
matches the clean specimen. Every Aadhaar specimen is judged against that one
application, so the reviewer changes *which specimen they upload*, not which
application they open, to show a different capability:

- clean → everything verifies;
- misread-name → the printed name is a near-match, flagged for review;
- tampered-QR → the QR contradicts the altered print;
- invalid-number → the checksum fails;
- impossible-DOB → the internal-consistency check catches a future date of birth
  from the document alone;
- wrong-person → the cross-checks against the application fail;
- cross-document → the applicant's PAN and a different person's Aadhaar, filed
  together, are reconciled against each other and disagree;
- poor-scan → the quality check warns;
- department-down → issuer verification is unavailable (the existing UIDAI
  force-down toggle on the clean specimen).

Rejected: one application per scenario. It multiplies seeded data for no gain — the
intrinsic checks (checksum, QR, quality) do not depend on the application at all, and
the cross-checks are clearer read against one fixed, honest identity.

## D2 — Real Gemini extraction, with a fallback that cannot mask a bad document

The demo runs on real Gemini (`EXTRACTION_MODE=gemini`). A live model call can fail
on stage for reasons that have nothing to do with the document — a dropped network,
a spent key — so `FallbackDocumentExtractor` sits Gemini over the mock reader and
falls through **only** on `ExtractionFailed` / `ExtractionCredentialMissing`, for
both classify and extract together. It is opt-in via `EXTRACTION_FALLBACK=1`, off by
default so tests and ordinary runs keep plain Gemini behaviour.

A genuine "this scan is unreadable" from the model is *not* a fallback trigger, and
neither is a `DocumentReadNotRegistered` wiring mistake — the net catches
infrastructure failing, never the document being bad. The mock reads for the
showcase carry the same authored `qr_fields` and quality the specimens do, so the
fallback still demonstrates each scenario rather than degrading to a bare read.

The automated test suite never calls real Gemini: it drives the mock reader, which
exercises the identical check engine.

## D3 — The QR-vs-print integrity check, and its honest boundary

Tamper detection here is a real, explainable comparison, not pixel forensics: decode
the QR the document carries and compare it, field by field, to what was read off the
print. A genuine card agrees in both; the tampered specimen has an altered print but
a QR that still carries the original identity, so the check reports the contradiction
and names the disputed field.

The boundary, stated plainly: a production Aadhaar carries an **encrypted, signed
secure-QR** this system does not decode. Our specimens carry a documented plain-text
QR (`AADHAAR|name=..|uid=..|dob=..|gender=..`) that we generate and control. So the
integrity *comparison* is genuinely real for our specimens, and the check degrades to
"no QR read" (INFO) on any document whose QR it cannot read — it never guesses.
Decoding is OpenCV's `QRCodeDetector` (no system package), tried on the whole page
then on a detected, upscaled crop.

## D4 — Turning on the Verhoeff checksum without breaking ADR-009

ADR-009 deliberately left the Aadhaar Verhoeff checksum off, because the legacy
seeded applications carry invented numbers that all fail it, and a checksum switched
off for the data it guards is worse than none. That reasoning still holds for that
data.

This pass turns the checksum **on, scoped to real extraction**: `AadhaarFormat.inspect`
takes a `verify_checksum` flag, off by default, and the check engine sets it true
only when the document carried a QR the system could read — which is the
real-extraction showcase path. Legacy mock reads carry no QR, so they keep the
structural-only check and their tests stay green. The showcase specimens carry
Verhoeff-valid numbers by construction (the generator computes the check digit), so
the clean specimen passes and the invalid-number specimen — twelve digits, valid
leading digit, deliberately wrong check digit — is caught by the checksum alone.

So ADR-009 is honoured, not contradicted: the checksum is enabled exactly where the
data was built to satisfy it, and named as a distinct `CHECKSUM_FAILED` verdict.

## D5 — Quality assessment is a heuristic, and says so

The scan-quality check is a legibility judgement, not an authenticity one. It scores
sharpness (variance of the Laplacian) and resolution over the rendered pages and
warns — never fails — when a scan is too blurred or small to rely on, because a
blurred photo of a real card is still a real card. It is honest about being a
heuristic, and absent entirely when quality was not assessed (the legacy path), so
nothing reports a false all-clear.

## D6 — Internal consistency: judging the document against itself

The intrinsic checks so far all looked at *fields* — a checksum on the number, a QR
against the print. The internal-consistency check adds the missing intrinsic angle:
does the document contradict *itself*, before any comparison to the application or a
sibling. The first, headline form is date-of-birth plausibility, because it is the
one every identity document carries and the one a fabricated or badly-read document
most obviously gets wrong.

It runs for any document that read a `dob`, and grades plausibility, not identity: a
date in the future or one implying an age over ~120 **fails** (`:internal-consistency`),
a year-only date (`yyyy-01-01`, the shape of a placeholder) or an unreadable one
**warns**, and a plausible date passes. It is a pure domain check wired into the
per-document engine alongside the format checks, so it fires for PAN, Aadhaar and any
future type with a DOB, not just the showcase.

Rejected for now: internal script-name agreement (the English vs regional-script name
lines on an Aadhaar). It needs a reliable read of the regional line, which the current
extraction does not give, so it would be a check that mostly abstains — a worse signal
than not having it.

## D7 — Cross-document consistency: the documents reconciled against each other

Every cross-check until now compared one document to the *application*. But two
identity documents filed together should also name the same *person* as each other,
and a disagreement between them is worth surfacing even when each sits close enough to
the application to pass on its own. The cross-document check is the first that reasons
across documents rather than at one document against the form.

It is thread-level, not part of the per-document engine: it runs after a document has
settled, re-reads the file, and compares this document's name against the names
already read off the other documents on it. It reuses the same `NameSimilarity` and
the same WARN grain the field checks use — a near-match is a look, not a failure — and
attaches a `:cross-document` check to the document being reconciled, naming the sibling
it disagrees with (e.g. "this reads Vikram Anand Reddy, but the PAN reads Rithika
Sharma"). A lone document has no sibling to compare against, so the check is simply
absent until a second identity document arrives.

Two honest limitations, both acceptable for the showcase and recorded here:

- It runs during analysis, on the last identity document to settle, so only that
  document carries the cross-document verdict; it is not re-derived for every document
  on the file. Re-running the analysis is what refreshes it.
- It is not recomputed when a field is edited by hand after the run — the reconciliation
  step only preserves external-issuer checks across a re-check, not this one.

Rejected for now: reconciling name **and** DOB together. Name alone is the clear,
demonstrable case; adding DOB is a later widening with no new machinery.

## Consequences

- New Aadhaar capabilities, each a real check with a stable id: `:aadhaar-format`
  (now also a checksum verdict), `:qr-consistency`, `:scan-quality`,
  `:internal-consistency` (per-document, DOB plausibility) and `:cross-document`
  (thread-level, name reconciliation) — all generated by the existing engine,
  streamed and rendered with no new UI plumbing.
- New extraction machinery, all no-system-dependency: `qr_decode` (OpenCV),
  `image_quality` (Pillow + numpy), `aadhaar_verhoeff` (pure), and a
  `FallbackDocumentExtractor`. `DocumentRecordDTO` gained optional `qr_fields` and
  `quality`, carried through to the check request.
- A deterministic specimen generator (`scripts/generate_aadhaar_specimens.py`,
  segno-generated QR, watermarked "SPECIMEN — NOT A REAL AADHAAR", no PII), which
  also emits the applicant's PAN (`pan_rithika.pdf`, "SPECIMEN — NOT A REAL PAN") as
  the second document in the cross-document scenario. A read-only demo endpoint lists
  and serves the specimens; scenarios are attached by dragging a specimen into the
  workspace (the endpoint is the source of truth for the scenario list).
- The cross-document scenario is the only two-document one: the PAN and the
  wrong-person Aadhaar are attached in turn, and the check fires on the second to
  settle.
- The tampered specimen is caught twice over — the QR contradiction *and* the
  application cross-check — which is more honest than engineering it to trip only
  one, and is asserted as such.
- The showcase is Aadhaar-only. Other types keep their existing behaviour untouched;
  the pattern is ready to repeat.
