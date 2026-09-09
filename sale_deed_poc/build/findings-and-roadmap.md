# Solution 4 — Findings & Build Roadmap

*Synthesis tying the two research studies (`research/01`, `research/02`) and the real-bundle test run
to concrete validator changes. This is the decision record; the studies are the evidence.*

---

## 1. Where the POC stands (verified)

- **Pipeline works end-to-end:** upload → two-pass inventory (segment a bundle into its documents) →
  per-document extraction (Gemini 3.1 Pro) → deterministic chain validation → report (timeline +
  chronology table + risk + provenance). 11 chain tests green.
- **Ingest handles real bundles:** `MAX_PAGES` 20→150 (configurable); all pages processed; inventory
  images downscaled to fit one request; truncation warned, never silent.
- **Inventory segments link deeds:** a 90-page bundle correctly split into **7 documents** (summary +
  DA-cum-GPA + sale deed + 2 certified-copy sale deeds + 2 partition deeds) once taught the
  certified-copy boundary cues ("Doc No. X/YYYY", "Copy of Document", "ATTESTED SUB-REGISTRAR").
- **Chain logic is parcel- and aggregation-aware:** seller matches *any* prior buyer **for the same
  parcel** (survey/plot); extent aggregates a seller's prior same-parcel purchases; name matching is
  overlap- and case-tolerant (`token_set_ratio` + `default_process`); severity is graduated by score.

## 2. Findings from the real 90-page bundle (the honest gaps)

Running the full pipeline on the real bundle surfaced **extraction/logic noise that inflated "broken":**

1. **Summary sheet treated as a deed.** The front "Registration Details / Link Documents" table got
   pulled into the chain as a node. **It is metadata, not a conveyance** (confirmed by `research/01`
   §2.5) — it must be excluded from chain nodes and instead used as a *claimed-chain cross-check*.
2. **Doc duplication / mislabel.** `2315/2026` appeared twice; one segment mis-extracted the DA.
3. **Missing dates/parties** on the oldest handwritten certified copies (e.g. a 1961 deed) → wrong
   chronological ordering.
4. **Transliteration variance** (e.g. a surname spelled two ways across deeds; same party on both sides) → false weak/broken.
5. **Overall "broken / risk 100" is inflated by 1–4**, not all real title breaks.

## 3. Research-grounded design conclusions

| Conclusion | Source | Implication for the validator |
|---|---|---|
| Chain continuity is a **3-way join**: party (vendee→vendor) ∧ citation (recital→predecessor doc-no) ∧ property (Schedule/survey) | 01 §2.3 | We do party + property + recital. Keep all three; require agreement. ✅ validates current direction |
| **Summary sheet = metadata**, not a deed | 01 §2.5, 02 | **Exclude from chain nodes**; parse it as a claimed chain to reconcile against |
| **GPA / Agreement / Will resting as the conveyance = broken title** (*Suraj Lamp* 2011) | 01 §3.4, 02 §1.7 | DOC rule: if a link's conveyance is a GPA/agreement/will → broken |
| **DA-cum-GPA does NOT transfer land title** — it's authority to develop + execute deeds | 01 §3.5 | **Reframe:** in the real bundle the DA-cum-GPA is *not* a title link; the chain runs through the sale/partition deeds |
| **Extent ledger per parcel** (sum of constituent extents = aggregate) | 01 §2.6 | Already implemented per-survey aggregation. ✅ |
| Data model: **registration tuple (`doc-no/year`+SRO) = primary key**, recitals = edge list, Schedule = join key | 01 §5.2 | Key nodes by the registration tuple; build edges from recital citations |
| **13y/30y search window** parameterizes completeness | 01 §2.4, 02 §1.1 | Add a configurable search-window; judge completeness within it |
| **Registration ↔ revenue-records mismatch = #1 fraud signal** | 02 §1.3 | Highest-value check, but PORTAL (RoR/1-B lookup) → Phase 2 |
| **EC / "Nil EC" ≠ title guarantee** | 02 §1.2 | Surface this caveat in every report; never present a clean result as a guarantee |

## 4. Build roadmap (DOC now · PORTAL phase-2 · JUDGEMENT human)

### Phase A — DOC checkpoints (buildable now, from documents we already extract)
1. **Exclude the summary sheet from chain nodes** (+ keep it as a claimed-chain cross-check). *(highest leverage — collapses most false "broken")*
2. **Treat DA-cum-GPA / GPA / Agreement / Will as authority/non-conveyance**, not a title link; a chain link resting on one of these = **broken** (Suraj Lamp). *(reframes the real bundle)*
3. **Registered-within-4-months** (§23): execution→registration ≤ 4 months → flag.
4. **Compulsorily-registered** (§17): flag reliance on an unregistered instrument.
5. **Seller-capacity red flags:** minor · POA/GPA execution · NRI+agri land · company · HUF.
6. **Certified-copy vs original:** certified copies → possible hidden equitable-mortgage flag.
7. **Name normalization** across transliteration variants (reduce false weak/broken).
8. **Date back-fill** from the registration endorsement when the deed body lacks a date.

### Phase B — PORTAL checkpoints (advisory; no official API → aggregators/manual; per earlier research)
EC retrieval · **22-A prohibited-property** · **RoR/1-B mutation ↔ registry mismatch** · guideline-value
/ under-stamping (§47-A) · e-stamp SHCIL verify · RERA registration · OC/CC. State-fragmented; AP IGRS /
TS Bhu Bharati. Treat as advisory, never authoritative.

### Phase C — JUDGEMENT (route to a human/lawyer, never auto-clear)
Marketable-title opinion · adverse possession / limitation · co-heir & succession disputes · physical
site/extent verification · CRZ/EIA borderline calls.

## 5. Prioritized next actions
1. **A1 + A2** (exclude summary, DA-cum-GPA as authority) — fixes the bulk of false "broken" on the real bundle.
2. **A5 wiring** (GPA-sale → broken) + **A3–A8 risk signals** (registration timeliness, capacity, certified-copy).
3. **Name normalization** + **date back-fill** to cut extraction noise.
4. Phase-B scoping: pick one aggregator/portal to prototype the registry cross-check (likely EC + 22-A).

## 6. Open decisions
- Default **search window** (13y vs 30y) and when to escalate.
- How to render **multi-parcel aggregation** in the timeline (logic handles it; the picture is still linear).
- Whether to **parse the summary table** into a structured claimed-chain now, or later.
- Phase-B: build vs buy for registry lookups (aggregator API vs manual/human-in-loop).

---
*Evidence: `research/01-deed-and-link-document-structure.md`, `research/02-sale-construction-rules-and-checkpoints.md`.
Not legal advice; a panel advocate should validate AP/TS specifics before production.*
