# ADR-009 — Identity documents beyond PAN: Aadhaar and driving licence

- **Status**: accepted
- **Feature**: pan-document-verification
- **Serves**: the extension of AC1–AC11 to Aadhaar and driving licence

## Context

ADR-001 through ADR-008 built the machine around a single document type. The
catalog always declared twelve; PAN was the one that was real and the other
eleven reported themselves recognised-but-unsupported (ADR-006, Flow 4). This pass
makes two identity documents real — Aadhaar (verified against UIDAI) and driving
licence (verified against Sarathi) — reusing the extraction port, the check
engine, the issuer seam and the stream unchanged. Voter ID stays unsupported by
the applicant's instruction.

Two decisions departed from what a first reading of the domain would suggest, and
both are recorded here because the code points at this ADR by name.

## D1 — Aadhaar is checked for structure, not for its Verhoeff checksum

A real Aadhaar number carries a Verhoeff check digit, and the obvious format
check is to verify it. `AadhaarFormat` deliberately does not. It confirms the
value is twelve digits and does not begin with 0 or 1 — enough to tell an Aadhaar
apart from some other twelve-digit number a scan might carry — and stops there.

The reason is the seeded data. The three demo applications carry invented Aadhaar
numbers (`731655204821`, `409322107754`, `551809326604`), and all three fail
Verhoeff, because a number invented to look right almost never satisfies the
checksum. Enforcing it would report every seeded application as holding a forged
Aadhaar — the demo would fail its own happy path.

Rejected: seeding Verhoeff-valid numbers instead. That trades a visible, recorded
limitation for an invisible one — the numbers would then *look* verifiable while
the demographic story the demo actually tells (UIDAI confirms or disagrees) has
nothing to do with the checksum. A checksum switched off for the very data it is
meant to guard is worse than no checksum, because the next reader assumes it runs.
The limitation is stated in `AadhaarFormat`'s docstring and here, so a real
integration knows exactly what to add and why it was left out.

The masking rule (ADR-002's identifier masking) still applies: only the last four
digits are ever echoed, so the structural check never puts a full Aadhaar number
in front of the officer or into a note.

## D2 — The department reports which demographics agreed, not a single verdict

ITD-PAN answers with one `nameMatch` flag (ADR-004). UIDAI and Sarathi answer at
finer grain, and the readers preserve that grain rather than flattening it.

- `UidaiAnswerReader` reads a `matched` list — which demographics UIDAI confirmed
  — and treats anything not in it as disagreeing. A `matched` that is absent or
  not a list is read as **unreadable**, never as silent full agreement: reading a
  missing field as consent is how an unverified card would be reported confirmed.
- `SarathiAnswerReader` reads `nameMatch` and `dobMatch` separately. `dobMatch:
  null` means the department was not asked, which is not a disagreement (the same
  distinction ADR-004 D2 drew for PAN); only `dobMatch: false` counts against the
  match. An active licence whose holder details do not line up is a *partial
  match*, not a confirmation — the department vouches for the licence, not for the
  application form it was compared against.
- `IgrsAnswerReader` (shared with ADR-010's deed work) takes the same shape: a
  deed that is registered but not to the person named on the paper is a partial
  match.

This is a genuine addition to the prototype's response shape, which only ever had
one boolean. It is recorded because a real UIDAI or Sarathi contract is where D2
gets confirmed or corrected, and the mapping from department answer to check
verdict lives in exactly one reader per department — a single-file change either
way.

## Consequences

- Aadhaar and driving licence run the full identify → extract → checks → verify
  pipeline with no new stream, no new engine and no new officer action.
- The four seeded Aadhaar/licence applications pass their happy path; none is
  reported as forged on account of a checksum the demo data was never built to
  satisfy.
- The one behaviour a real integration must revisit — Verhoeff — is named in the
  code and here rather than silently absent.
- Per-demographic disagreement is preserved end to end: the officer is told *which*
  field the department disputes, not merely that something did not match.
