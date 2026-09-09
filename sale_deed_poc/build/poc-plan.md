# Solution 4 — Sale Deed Chain Validator · POC Plan

**One line:** feed it the stack of deeds for a property; it reconstructs the ownership chain,
verifies every transfer links up, and flags gaps/risks with evidence — turning hours of manual
title reading into a minutes-long, explainable screening.

**Design spine:** *the AI reads, the code judges.* Extraction (messy scans → structured data) is the
model's job; the verdict (is the chain intact?) is deterministic code — so it's explainable, testable,
and defensible in a govt/audit context. Safety-critical decisions stay code-owned, model-independent.

---

## 1. What can be analyzed (the analysis surface)

Organized as tiers — the POC commits to Tiers 0–2, demonstrates a slice of Tier 3, and *stubs* Tier 4.

### Tier 0 — Extraction (per deed)
- **Doc metadata:** doc no, SRO, registration & execution dates, book/CD/volume, **deed type**.
- **Parties:** vendors[] / vendees[] with relation (s/o · w/o · d/o), age, address, **PAN/Aadhaar** if present, **GPA/POA holder** if execution is via power of attorney.
- **Property:** survey no, plot no, khata/municipal no, **extent** (normalise sq yd ⇄ sq ft ⇄ sq m ⇄ acre-guntas), **boundary schedule** (N/S/E/W), village/mandal/district, **ULPIN** if printed.
- **Financials:** consideration, market value, **stamp duty paid**, registration fee, **e-stamp certificate no**, mode of payment.
- **Flow-of-title recital:** the "vendor acquired under Doc X at SRO Y on date Z" reference — the spine of chain-linking.
- **Declarations & endorsements:** "free from encumbrances" statements, registration endorsement, witnesses, QR/signature presence.

### Tier 1 — Single-deed analysis (each deed alone)
- **Completeness** — are all mandatory parts present (property schedule, consideration, execution, registration endorsement)?
- **Internal consistency** — amount in words == figures; extent in schedule == extent in body; boundary schedule coherent.
- **Deed-type truth check** — *is this actually a title-conveying sale?* Flag if it's really a **GPA / Agreement-to-Sell / unregistered** instrument (GPA "sales" are legally weak post the 2011 *Suraj Lamp* ruling) — a high-value catch.
- **Stamp-duty adequacy** — paid duty vs expected (approx, by state rate) → under-stamping = impoundable defect.
- **Party red flags** — minor seller (needs court sanction), GPA/POA execution, NRI (FEMA), agricultural land (state restrictions).

### Tier 2 — Chain analysis (across deeds) — the core IP
- **Identity continuity** — buyer(N) == seller(N+1); transliteration-tolerant, disambiguated by father/spouse name + address + PAN.
- **Property continuity** — same survey/plot; boundary schedule consistent.
- **Extent arithmetic** — area reconciles; sub-division (sells part) vs the **"sells more than they own"** signal (a missing deed / fraud flag — the money-shot in the sample report).
- **Recital linkage** — deed N+1 cites deed N as its source of title; broken recital = gap.
- **Temporal continuity** — dates run forward; a large gap = a possibly missing intermediate transfer.
- **Root completeness** — does the chain trace back to a **mother deed / govt allotment / patta**, or dangle?
- **Transfer-mode awareness** — distinguish a **missing *registered* deed** from a legitimately **non-registrable transition** (inheritance / partition / court decree need heir/decree docs, not a sale deed). Avoids false "broken chain" alarms.

### Tier 3 — Risk & fraud signals (the value multiplier; POC shows a subset)
- **GPA-sale flag** · **under-valuation / under-stamping** · **suspicious price movement** (flat/falling = distress/benami signal).
- **Boundary drift** across deeds → possible different/misdescribed property.
- **Encumbrance contradiction** — "free from encumbrance" claimed while a prior mortgage shows unreleased.
- **(Image-level, optional)** tamper/forgery signals — inconsistent fonts, missing registration endorsement/QR.

### Tier 4 — Registry & authenticity (Phase-2, advisory — per the research)
- **e-Stamp verification** via SHCIL (cert no → genuine + value + parties).
- **PKI digital-signature validation** on registry-issued PDFs (offline, robust).
- **QR decode** on TN/MH/KA registry documents.
- **EC cross-check** via aggregator (Landeed/Surepass) → "did the bundle miss a registered deed?".
> **Reality (researched):** India has **no official title-lookup API**. Direct registry retrieval is
> CAPTCHA/Aadhaar-OTP, manual. So Tier 4 is *advisory* and partly outsourced — flagged honestly, never
> presented as authoritative.

---

## 2. Value props we can credibly project in the POC

Each is demoable on real sample deeds — not a slideware claim.

1. **Minutes, not days.** A preliminary title read that takes an associate/lawyer hours → produced in minutes. *(Directly hits the project's core TAT pain.)*
2. **Reads the hard documents.** Vernacular, scanned, handwritten-endorsed deeds — multilingual OCR + understanding in one pass. This is the genuinely hard part, and the differentiator.
3. **Catches the missing deed.** Extent-arithmetic + recital-gap detection surfaces an incomplete/fraudulent chain a human skims past. **The demo money-shot.**
4. **Explainable, not black-box.** Every flag cites the exact field/recital it's based on — defensible for a government/audit setting.
5. **Structured output.** A pile of PDFs → a clean JSON ownership graph a downstream system (e.g. BuildNow permit flow) can consume.
6. **Triage at scale.** Auto-pass clean chains, escalate only the flagged ones → cuts manual review load. Shadow-safe, like Solution 2.
7. **(Phase-2 teaser)** authenticity cross-check (e-stamp/QR/signature) — shows the path to registry-grade verification.

**Honest POC boundary:** the POC proves *extraction quality + chain logic + explainable reporting* on a
handful of real samples. It does **not** prove scale, registry integration, or legal completeness — and it
**flags for a human, never auto-clears** title.

---

## 3. Implementation plan (phased — each phase is independently demoable)

| Phase | What | Deliverable | Proves | Est. |
|---|---|---|---|---|
| **0 · Scaffold** | folders, **deed JSON schema** (the extract⇄chain contract), model wrapper, CLI skeleton | `schema.py`, `run.py` stub | structure | 0.5d |
| **1 · Extract (1 deed)** ⟵ *de-risk first* | vision-LLM → strict JSON + confidence + low-conf flags; iterate on **real** samples | `extract.py` + JSON for a real deed | **the hard part works** (go/no-go gate) | 1–1.5d |
| **2 · Single-deed analysis + report-of-one** | completeness, internal consistency, deed-type, stamp/red-flags; render one deed | `analyze_deed.py` + 1-deed report | per-deed intelligence | 1d |
| **3 · Chain link + validate** ⟵ *core IP* | identity/property/recital/temporal/**extent** checks → link verdicts → overall; handle non-registrable transitions | `chain.py` + full timeline | **the differentiator** | 1.5d |
| **4 · Report polish + demo** | real data → timeline report; one-command demo | `run.py samples/X/ → out/report.html` | the deliverable | 0.5–1d |
| **5 · (opt) authenticity stub** | e-stamp no extraction + stubbed/real SHCIL check; note aggregator path | Tier-4 teaser | the Phase-2 story | 0.5d |

**Total POC ≈ 5–6 focused days**, committed incrementally (one phase = one coherent commit).
Build order deliberately **de-risks extraction first** (Phase 1) — if real scans don't extract cleanly,
we learn it cheaply before building the chain engine on top.

### Tech stack
- **Python.** PDF render `pypdfium2`/`pdf2image`; images `Pillow`.
- **Extraction:** **Gemini** primary (Indian-language strength + cost), abstracted behind one `extract()`
  call → swappable to **Claude** as fallback (resilience principle). Structured output via JSON schema.
- **Chain logic:** pure Python + `rapidfuzz` for transliteration-tolerant name matching.
- **Report:** `Jinja2` → the HTML template already built. No framework, no DB — JSON on disk.

### Unit map (focused files, single purpose)
```
Solution4/build/poc/
  schema.py       # the deed record contract (extract ⇄ chain boundary)
  ingest.py       # PDF/image → page images
  extract.py      # images → structured deed JSON (AI)
  analyze_deed.py # per-deed checks (Tier 1)
  chain.py        # cross-deed validation + verdict (Tier 2, deterministic)
  report.py       # JSON → HTML (Jinja2)
  run.py          # CLI orchestrator
```

### Risks / landmines (flag early, fail safe)
- **Extraction on old/handwritten/regional scans is risk #1** → Phase 1 is the gate, not an afterthought.
- **Name transliteration matching is genuinely hard** → fuzzy + father/spouse/address disambiguation; accept residual uncertainty → **flag, don't guess**.
- **Legal nuance** (non-registrable transitions, state rules) → encode common cases, flag the rest, **never auto-clear**.
- **Sample-data dependency** → POC quality is bounded by what we can test on. Need real deeds (ideally a linked chain) early.

---

## 4. Open forks (need your call before/early in the build)
1. **Report shape** — timeline-first (current mockup) vs pass/fail-table-first?
2. **Check set** — are Tier-2's five checks right, or add extent-arithmetic / encumbrance-contradiction to the core (vs Tier 3)?
3. **Phase-2 authenticity** — include the e-stamp/SHCIL stub in the POC, or keep the POC purely extract+chain?
4. **Sample data** — where are your samples, and is it a linked chain or single deeds? (Bounds what Phase 3 can prove.)
