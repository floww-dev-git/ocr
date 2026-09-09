# Aadhaar capability showcase — demo script

A single application, **BN/2026/0601 (Rithika Sharma)**, holds the applicant's true
declared identity. Every Aadhaar specimen is judged against it, so uploading a
different specimen lights up a different capability. The specimens are synthetic
(watermarked "SPECIMEN — NOT A REAL AADHAAR"); no real PII.

## Before the demo

```bash
# Generate the specimens (once; deterministic).
cd backend && uv run python scripts/generate_aadhaar_specimens.py
# -> backend/samples/aadhaar/{aadhaar_clean,aadhaar_tampered_qr,
#    aadhaar_invalid_number,aadhaar_mismatch,aadhaar_poor_scan,aadhaar_name_typo,
#    aadhaar_impossible_dob,pan_rithika}.pdf

# Serve with REAL Gemini extraction and the mock safety net underneath, so a
# dropped network or spent key cannot stop the demo on stage.
EXTRACTION_MODE=gemini EXTRACTION_FALLBACK=1 GEMINI_API_KEY=... \
  DI_SERVER_PORT=8000 uv run uvicorn config.asgi:application --port 8000

# terminal 2
cd frontend && npm run dev     # http://127.0.0.1:5173
```

Open **BN/2026/0601**. The **Demo** menu (top bar) lists the Aadhaar scenarios; each
attaches the specimen and runs it in one click. (You can also drag any specimen PDF
from `backend/samples/aadhaar/` into the workspace.)

## The scenarios

| Scenario | Specimen | What the reviewer sees | Capability shown |
| --- | --- | --- | --- |
| **Clean** | `aadhaar_clean.pdf` | Every check green; verified; UIDAI confirms | Identification, field extraction with confidence + provenance boxes, checksum PASS, QR-vs-print PASS, quality PASS, cross-checks PASS, issuer verification |
| **Misread name** | `aadhaar_name_typo.pdf` | Name reads "Ritika" for "Rithika" (93% similar) → "Needs a look" with the score; needs a look | Fuzzy name matching — a near-match is flagged for review, not rejected. The QR carries the correct spelling (so QR-vs-print is clean — a misread, not a tamper), and the department vouches for the card while noting the name, so the misread shows up twice over |
| **Tampered — QR ≠ print** | `aadhaar_tampered_qr.pdf` | "QR code contradicts the printed details" (name + number); document flagged | Real QR decode + integrity check (the honest tamper signal) |
| **Invalid number** | `aadhaar_invalid_number.pdf` | "Aadhaar number fails its checksum"; failed | Real Verhoeff checksum validation |
| **Impossible date of birth** | `aadhaar_impossible_dob.pdf` | "The date of birth is in the future"; failed, caught before any comparison | Internal-consistency check — the document is judged against itself (a future/absurd DOB), from the document alone |
| **Wrong person** | `aadhaar_mismatch.pdf` | Name and date of birth disagree with the application; failed | Cross-document field matching against the application (fuzzy name, exact date) |
| **Cross-document — PAN vs Aadhaar** | `pan_rithika.pdf`, then `aadhaar_mismatch.pdf` | The PAN reads clean against the application; the Aadhaar then carries "Name does not match another document", naming the PAN it disagrees with | Cross-document consistency — the identity documents on one file are reconciled against **each other**, not just the application |
| **Poor scan** | `aadhaar_poor_scan.pdf` | "Scan quality is poor — verify against the original"; needs a look | Document quality assessment |
| **Department down** | `aadhaar_clean.pdf` + Demo → "Never respond" | UIDAI could not be reached; retry offered | Issuer verification unavailable + retry |

The **Cross-document** scenario is the only two-document one: attach the applicant's
PAN first, then the "Wrong person" Aadhaar. The check runs on the second document to
settle, comparing its name against the ones already read off the file — so it names
the PAN on the Aadhaar's report.

## Notes to say out loud (honest boundaries)

- The QR check reads the **plain-text QR our specimens carry**, which we control. A
  production Aadhaar carries an encrypted, signed secure-QR we do not decode — the
  capability shown is the integrity *comparison*, on a QR we can read.
- "Tamper" here means the QR and the print disagree — a real, explainable signal —
  not pixel forensics.
- Quality assessment is a heuristic (scan sharpness + resolution); it judges
  legibility, not authenticity.
- The internal-consistency check on the DOB is plausibility, not identity: a future
  date or one implying an age over ~120 fails; a year-only date (`yyyy-01-01`) or an
  unreadable one is a "needs a look", not a failure.
- The cross-document check runs during analysis, on the last identity document to
  settle on the file — so it names the siblings already read. It is not recomputed
  when a field is later edited by hand; re-running the analysis is what refreshes it.
- Extraction is real Gemini; the mock reader is only a fallback so the demo cannot
  hard-fail. Which engine produced a result is surfaced when the fallback is used.
- The PAN specimen (`pan_rithika.pdf`) is a plain synthetic card (watermarked
  "SPECIMEN — NOT A REAL PAN"), enough to read a name/DOB/PAN off for the
  cross-document scenario; it is not a faithful PAN reproduction.
