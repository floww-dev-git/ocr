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
#    aadhaar_invalid_number,aadhaar_mismatch,aadhaar_poor_scan}.pdf

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

## The six scenarios

| Scenario | Specimen | What the reviewer sees | Capability shown |
| --- | --- | --- | --- |
| **Clean** | `aadhaar_clean.pdf` | Every check green; verified; UIDAI confirms | Identification, field extraction with confidence + provenance boxes, checksum PASS, QR-vs-print PASS, quality PASS, cross-checks PASS, issuer verification |
| **Misread name** | `aadhaar_name_typo.pdf` | Name reads "Ritika" for "Rithika" (93% similar) → "Needs a look" with the score; needs a look | Fuzzy name matching — a near-match is flagged for review, not rejected. The QR carries the correct spelling (so QR-vs-print is clean — a misread, not a tamper), and the department vouches for the card while noting the name, so the misread shows up twice over |
| **Tampered — QR ≠ print** | `aadhaar_tampered_qr.pdf` | "QR code contradicts the printed details" (name + number); document flagged | Real QR decode + integrity check (the honest tamper signal) |
| **Invalid number** | `aadhaar_invalid_number.pdf` | "Aadhaar number fails its checksum"; failed | Real Verhoeff checksum validation |
| **Wrong person** | `aadhaar_mismatch.pdf` | Name and date of birth disagree with the application; failed | Cross-document field matching (fuzzy name, exact date) |
| **Poor scan** | `aadhaar_poor_scan.pdf` | "Scan quality is poor — verify against the original"; needs a look | Document quality assessment |
| **Department down** | `aadhaar_clean.pdf` + Demo → "Never respond" | UIDAI could not be reached; retry offered | Issuer verification unavailable + retry |

## Notes to say out loud (honest boundaries)

- The QR check reads the **plain-text QR our specimens carry**, which we control. A
  production Aadhaar carries an encrypted, signed secure-QR we do not decode — the
  capability shown is the integrity *comparison*, on a QR we can read.
- "Tamper" here means the QR and the print disagree — a real, explainable signal —
  not pixel forensics.
- Quality assessment is a heuristic (scan sharpness + resolution); it judges
  legibility, not authenticity.
- Extraction is real Gemini; the mock reader is only a fallback so the demo cannot
  hard-fail. Which engine produced a result is surfaced when the fallback is used.
