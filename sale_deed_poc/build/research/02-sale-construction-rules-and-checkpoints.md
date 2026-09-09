# Legal Rules, Due-Diligence Checkpoints & Regulatory Gates for Property Sale and New Construction in India

**A reference document for an automated title / compliance validation system (BuildNow / Urbanflow)**
*National coverage, weighted to Andhra Pradesh (AP) and Telangana (TS). Current as of mid-2026; time-versioned items are flagged.*

> **How to read this doc.** Each checkpoint states **WHAT** it verifies and **WHY** it matters, and is tagged with a verifiability class the engine can act on:
> - **[DOC]** verifiable from the documents alone (intrinsic consistency / presence checks)
> - **[PORTAL]** verifiable by a deterministic registry/portal lookup (automatable, but state-fragmented)
> - **[JUDGEMENT]** requires human / legal judgement (not safely automatable; flag for a lawyer)
>
> **Architectural insight that should shape the whole product:** in India, **registration** (who holds legal title, under the Transfer of Property Act + Registration Act) and **revenue/land records** (who possesses/pays tax, in the RoR) are *independent systems with different verification standards*. The highest-value automated check is **cross-verifying registry records against revenue records and litigation** — that mismatch is exactly the gap fraudsters exploit, and the gap that ULPIN/Bhu-Aadhaar, Dharani→Bhu Bharati, and SAMPADA 2.0 are trying to close.

---

## PART 1 — Title & Ownership Due-Diligence (Property Purchase)

### 1.1 Chain of title / link documents (the "13 vs 30 year" search)
- **Mother deed → unbroken chain.** Every transfer (sale, inheritance, gift, partition) must have a corresponding **registered** document, each connecting continuously to the next. A single gap/defect renders the *entire* title defective. **[DOC]+[JUDGEMENT]**
- **30-year "Full Search"** is standard for high-value/complex titles and required by most PSU banks: (a) limitation against the **State is 30 years**; (b) **Evidence Act §90** presumes 30+ year-old documents validly executed.
- **13-year (~12-year) "Limited Search"** is the floor: **adverse possession** can extinguish title after **12 years** (Limitation Act Art. 65).
- **Bank rule of thumb:** loans **> ₹1 crore → 30-year search** with certified copies; smaller loans may accept 13-year.
- **"Registration alone does not cure title defects."** Output artifact: an advocate **Title Search Report (TSR)**.

### 1.2 Encumbrance Certificate (EC) — power and hard limits
- **What it shows:** all **registered** transactions over a period — sales, mortgages, gifts, releases, court attachments. Primary tool to catch a **prior mortgage** or **double sale**. **[PORTAL]**
- **AP/TS forms:** **Form 15** = transactions exist; **Form 16 = "Nil EC."** Via IGRS (AP `registration.ap.gov.in`; TS `registration.telangana.gov.in`) / MeeSeva; TS agri land via Bhu Bharati. Mirror the title-search period (13/30 yrs).
- **CRITICAL BLIND SPOTS — a "Nil EC" is NOT proof of clean title.** EC captures **only registered** events. It does **not** show: unregistered/equitable (oral) mortgages, unregistered settlements/oral partition, unregistered GPA/will, short leases (<1 yr), **property-tax arrears**, society/utility dues, or **pending litigation**. The engine must explicitly warn that EC ≠ title guarantee.

### 1.3 Revenue records: mutation / khata / patta / RoR — Pahani, Adangal, 1-B
- **Possession ≠ ownership.** A **mutation entry neither creates nor extinguishes title** (SC: *Sawarni v. Inder Kaur* 1996; *Bhimabai Mahadeo Kambekar* 2019). **[JUDGEMENT]**
- **Pahani/Adangal:** owner, survey no., extent, possession, crop — proves **possession, not title.** **[PORTAL]**
- **RoR / 1-B:** the ownership extract (owner, survey/sub-division, khata, extent, mutation history; AP/TS include **Prohibited Status**). **[PORTAL]**
- **State portals:** **AP — MeeBhoomi** (`meebhoomi.ap.gov.in`) over **Webland** (AP RoR Act 1971; TD-cum-Pattadar Passbook is evidentiary). **TS — Dharani → Bhu Bharati.**
- **The fraud gap:** a mutation can be obtained **without co-owners' knowledge**; revenue records don't surface suits/injunctions. **A registration ↔ revenue mismatch is a primary fraud red flag.** **[PORTAL → cross-check]**

### 1.4 Property-tax receipts
- **Latest paid receipts** confirm no municipal/panchayat arrears + corroborate owner/possession. Arrears do **not** appear on the EC — check separately. **[PORTAL]**

### 1.5 Survey number / sub-division / FMB / LPM consistency
- **FMB (Field Measurement Book):** survey number, division, extent, khata, and **boundaries/vertices**; each survey number splits into **sub-divisions** held by different owners. **[PORTAL]+[JUDGEMENT]**
- **Most common land fraud:** the survey number/extent on the deed doesn't match the physical plot or revenue record. Deed survey no./sub-division/extent **must match FMB *and* RoR/1-B**; a **physical site visit + measurement** is essential. **[JUDGEMENT]**
- **TS shift to LPM:** under the **TS RoR Act 2025 / Bhu Bharati**, drone-surveyed geo-referenced **LPM numbers** replace old survey numbers; GPS boundary takes precedence.

### 1.6 Litigation, lis pendens & court attachments
- **Lis pendens — §52 TPA:** while a suit directly involving the property is pending, a transfer by a party is **void against the eventual decree** (buyer takes subject to outcome). **[PORTAL]+[JUDGEMENT]** (eCourts). Land disputes are the largest segment of Indian civil litigation.

### 1.7 Seller identity & capacity (the "who can sign" gate)

| Seller type | Rule | Tag |
|---|---|---|
| **Minor** | §8 Hindu Minority & Guardianship Act 1956 — guardian **cannot** sell minor's immovable property **without court permission**; sale **voidable at minor's instance**. | DOC+JUDGEMENT |
| **POA / GPA** | *Suraj Lamp v. Haryana* (2012) 1 SCC 656 (11-Oct-2011) — "SA/GPA/WILL" transfers **convey no title**; need a **registered sale deed**. Title resting on a GPA-"sale" is **presumptively defective**; a POA used only for *signing* must be genuine, registered, in-scope, unrevoked. | DOC+JUDGEMENT |
| **NRI/OCI/PIO** | **Cannot buy agricultural land / plantation / farmhouse** (only residential/commercial). May acquire agri land only by **inheritance**; may sell inherited agri land only to a resident. Violation void + penalty up to **3×** (§13 FEMA). | DOC+JUDGEMENT |
| **Company** | Sale within **MOA object clause**; *ultra vires* act void, can't be ratified. Verify board resolution + MOA/AOA. | DOC+JUDGEMENT |
| **HUF / joint family** | Coparcenary property needs **all coparceners' consent**; Karta may sell only for **legal necessity**. Post-2005, **daughters are coparceners** — consent required. | JUDGEMENT |
| **Legal heirs** | **Legal Heir Certificate** for immovable-property mutation; **Succession Certificate** (civil court) for movables. One heir transferring without others **taints title**. | DOC+JUDGEMENT |

### 1.8 Agricultural land: conversion, ceiling, prohibited property
- **NALA conversion (agri → non-agri)** prior permission required. **AP:** Act 3 of 2006, OTC ~**3%** of basic value (50% penalty if unauthorized) — *(AP cabinet approved a draft repeal Aug 2025 — verify status).* **TS:** Act 3 of 2006, ~**5% (GHMC)/9% (other)** — *(rates vary by source; treat live GO/portal as source of truth).*
- **Land ceiling:** surplus land barred from registration (falls under 22-A).
- **Prohibited property — §22-A Registration Act (AP/TS amendment):** auto-blocks registration. Categories: 22A(1)(a) assigned lands · (b) government lands · (c) endowment/temple/Wakf/charitable · (d) ceiling-surplus · (e) notified govt-interest (needs **Gazette notification**). **Free portal check** on IGRS by district/mandal/village + survey/door. **[PORTAL]** *(AP removed five categories from the 22-A list Jan 2026.)*
- **A clean EC does NOT mean not-prohibited** — 22-A is a *separate* mandatory check.

### 1.9 ULPIN / Bhu-Aadhaar
- **14-digit** unique parcel ID from lat/long under DI-LRMP; stays permanently attached through transfers/sub-divisions; rolled out across 29 states incl. AP. Intended to "identify actual landowners and prevent fraud." **[PORTAL]**

---

## PART 2 — Stamp Duty, Registration & Valuation Gates

### 2.1 Valuation basis: the "higher of" rule
- **Stamp duty is charged on the HIGHER of (a) stated consideration or (b) government guideline/market value** (circle/basic/unit rate). **Engine gate: fail if duty computed only on consideration when guideline value is higher.** **[PORTAL]**
- **TS market value:** `registration.telangana.gov.in` → Market Value Search (revised **1-Apr-2025**). **AP:** `registration.ap.gov.in/igrs/newPropertyvalue` + Duty/Fee Calculator (AP urban values revised **1-Feb-2026**). **Pull live, don't hard-code.**

### 2.2 Current sale-deed rates (verify against live calculators)
- **Telangana:** Urban ~**6% = 4% SD + 0.5% reg + 1.5% transfer**; Rural ~**7.5%**. Family gift 2%.
- **AP:** slab-based **5% ≤₹50L / 6% ₹50L–1Cr / 7% >₹1Cr** + 1% reg + 1.5% transfer (~7.5% combined at ≤₹50L). *(One source lists flat 5% SD — verify on live IGRS AP calculator.)*

### 2.3 Under-valuation / under-stamping (Indian Stamp Act 1899)
- **§47-A:** Registering Officer may refer to the **Collector** to determine true market value + deficient duty (appellate authority can enhance).
- **§33:** authorised officer **must impound** an under-stamped instrument.
- **§35:** under-stamped instrument **not admissible / not registrable** unless duly stamped; penalty = deficient duty **+ ₹5 or 10× deficient duty, whichever greater.**

### 2.4 Mandatory registration (Registration Act 1908)
- **§17(1):** compulsory registration of immovable-property documents worth **≥ ₹100** (sale/gift/partition/settlement, leases > 1 yr).
- **§49:** an unregistered compulsorily-registrable document **cannot be evidence** (can't pass title).
- **§23:** present for registration **within 4 months** of execution. **Engine gate: execution→registration ≤ 4 months.**

### 2.5 e-Stamp verification (SHCIL)
- **SHCIL** = MoF-authorised Central Record Keeping Agency for e-stamping; each e-stamp has a **UIN**; verify via UIN/QR on SHCIL's "Verify e-Stamp" page (or the EStamping app, even offline). **[PORTAL] — directly automatable.**

### 2.6 TDS gate — §194-IA Income-Tax Act
- Buyer must deduct **1% TDS** on the **higher of consideration or stamp-duty value** when **either ≥ ₹50 lakh** (not rural agri). Form 26QB within 30 days; **no PAN → 20%**. **[DOC/PORTAL]**

### 2.7 Registration process in AP/TS (CARD → IGRS)
- **CARD** computerised registration ("anywhere registration"); IGRS TS holds non-agri records back to **1983**. **Mandatory slot booking + biometric/Aadhaar verification** of buyer, seller, two witnesses.

---

## PART 3 — Construction / Development Approval Gates (BuildNow)

### 3.1 Land use / zoning / master-plan & Change of Land Use (CLU)
- Construction must conform to master plan/zoning (CRDA/DTCP/HMDA/municipal). Agri land needs **NALA** first. DTCP-level CLU needs a Gazette notification (15-day objection window; §15(1) AP Town Planning Act 1920).

### 3.2 Layout approval (open plots) — LP numbers, LRS/BRS
- **TS:** HMDA (Hyderabad) / DTCP (elsewhere); valid **LP number** = approved layout (verify on HMDA DPMS). In approved TS layouts ~**15% is mortgaged/locked** by the authority (developer sells ~85%).
- **Unapproved layouts → no building permission, no loan, no permanent utilities, possible demolition.**
- **AP LRS 2020** (G.O.Ms.10, 08-01-2020; cut-off pre-31-08-2019 registered plot; re-opened G.O.Ms.134, 26-07-2025). **TS LRS** G.O.Ms.131 (2020), `lrs.telangana.gov.in`. **BRS** regularises buildings.

### 3.3 Building plan sanction — setbacks, FSI/FAR, height, coverage
- **TS — TG-bPASS** (Act 2020), banded by plot size:
  - **Instant Registration — ≤75 sq yd** (G/G+1): no permission, **no OC**.
  - **Instant Approval — ≤500 sq m and ≤10 m** (residential): instant self-cert.
  - **Single-Window — >500 sq m or >10 m** (& all non-residential): NOCs via CAF, sanctioned **within 21 days**.
  - These plot-size bands are the cleanest deterministic gates. **[DOC/PORTAL]**
- **AP — Building Rules 2017** (G.O.Ms.119): Rule 57 setbacks/height (non-high-rise), Rule 62 high-rise, Rule 66 open spaces; min **1.50 m setback for buildings > 10 m**.
- **TS setbacks** by **road-width bands** + height; **high-rise threshold = 18 m**.
- *FSI/FAR/coverage/setbacks are state- and road-width-parameterised — model as per-state config, not constants.*

### 3.4 NOCs

| NOC | Trigger | Authority | Tag |
|---|---|---|---|
| **Fire** | Buildings **> ~15 m** (NBC 2016; some states 12 m); prerequisite to OC | State Fire Dept | DOC+PORTAL |
| **Environmental (EIA 2006)** | Built-up **≥ 20,000 sq m** (B2 20k–150k; B1 >150k or >50 ha) | SEIAA/MoEFCC | DOC+JUDGEMENT |
| **Airport/AAI** | Structures **within 20 km** of aerodrome; >150 m → NOCAS | AAI/NOCAS | DOC+PORTAL |
| **Coastal (CRZ 2019)** | Within CRZ; CRZ-II cleared at State (SCZMA) | SCZMA/MoEFCC | JUDGEMENT |
| **Pollution (CFE/CFO)** | CFE before construction; CFO before operations (Water/Air Acts) | State PCB | PORTAL+JUDGEMENT |

- **EIA landmine:** 2016 self-certification notification set aside (NGT 2017); **2025 SC struck down exemptions** — any project **> 20,000 sq m needs EIA/SEIAA.** **Safest rule: ≥20,000 sq m ⇒ require EIA, regardless of "self-certification."**

### 3.5 RERA
- **Mandatory when land > 500 sq m OR > 8 apartments** (permissions on/after 01-01-2017). Register **before selling any unit**. **70% escrow**; **carpet-area** sale mandatory. TS `rera.telangana.gov.in`. **[PORTAL]**

### 3.6 Occupancy / Completion Certificate (OC/CC)
- **OC** certifies the building matches approved plans + is safe; **mandatory before selling/handing over.** SC held offering possession without OC + fire clearance is illegal. No OC → illegal occupation, no loans, utilities refused. **[DOC/PORTAL]**

### 3.7 Common construction pitfalls
- Building **without sanction**; **deviations**; **unapproved layouts** (LRS) / **unauthorised buildings** (BRS); legacy layouts needing **roads/open spaces gift-deeded to gram panchayat**; selling **without OC**.

---

## PART 4 — Software-Enforceable Checkpoint Matrix (Red Flags)

Gate on **[DOC]/[PORTAL]**; route to a lawyer on **[JUDGEMENT]**. Fail in the **safe direction** (over-flag, escalate).

### (a) Title / ownership
| # | Checkpoint | Tag |
|---|---|---|
| A1 | Unbroken chain of registered link documents over 13/30 yrs; mother deed identified | DOC+JUDGEMENT |
| A2 | Deed names/IDs consistent across chain; no tamper signs (erasures, font/ink mismatch, missing pages/sigs/reg nos) | DOC |
| A3 | Seller = current registered owner in RoR/1-B (registry ↔ revenue match) | PORTAL |
| A4 | Property changed hands many times in a short period (double-sale signal) | PORTAL |
| A5 | Title rests on a **GPA "sale"** rather than registered conveyance (Suraj Lamp) | DOC+JUDGEMENT |
| A6 | Seller capacity OK (minor/POA/company/HUF/NRI/heirs per §1.7) | DOC+JUDGEMENT |
| A7 | Originals produced (not just certified copies → hidden equitable-mortgage risk) | DOC+JUDGEMENT |
| A8 | Survey/sub-division/extent on deed match FMB **and** RoR; site-verified | PORTAL+JUDGEMENT |
| A9 | Marketable-title opinion (gaps, adverse possession, co-heir disputes) | JUDGEMENT |

### (b) Statutory / encumbrance
| # | Checkpoint | Tag |
|---|---|---|
| B1 | EC clean over 13/30 yrs — but flag "Nil EC" ≠ clean title | PORTAL |
| B2 | **Not** on §22-A prohibited list | PORTAL |
| B3 | No pending litigation / lis pendens / attachment (eCourts) | PORTAL+JUDGEMENT |
| B4 | Property-tax / utility / society dues cleared | PORTAL |
| B5 | Mutation current & consistent with registry; no unilateral single-heir mutation | PORTAL+JUDGEMENT |
| B6 | Agri land: NALA conversion where non-agri use intended | PORTAL+DOC |

### (c) Valuation / stamp
| # | Checkpoint | Tag |
|---|---|---|
| C1 | Duty on **higher of** consideration vs guideline value | PORTAL |
| C2 | SD + reg fee + transfer duty match current state slab | PORTAL |
| C3 | e-stamp UIN/QR authentic on SHCIL | PORTAL |
| C4 | Registered within 4 months of execution (§23) | DOC |
| C5 | Compulsorily registered (§17); not unregistered deed | DOC |
| C6 | TDS 194-IA (1%) where value ≥ ₹50L (Form 26QB) | DOC/PORTAL |
| C7 | Gross under-valuation vs guideline (§47-A / fraud signal) | PORTAL+JUDGEMENT |

### (d) Construction / approval
| # | Checkpoint | Tag |
|---|---|---|
| D1 | Use conforms to master plan/zoning; CLU done if needed | PORTAL+JUDGEMENT |
| D2 | Approved layout with valid LP number (not LRS-pending) | PORTAL |
| D3 | Building plan sanctioned; setbacks/FSI/FAR/height within rules | DOC+PORTAL |
| D4 | NOCs per triggers: Fire (>15m), EIA (≥20,000 sq m), AAI (≤20km/>150m), CRZ, PCB | DOC+PORTAL |
| D5 | RERA-registered if >500 sq m or >8 units; carpet-area; 70% escrow | PORTAL |
| D6 | OC/CC before possession/sale | PORTAL |
| D7 | No deviation beyond sanctioned plan | JUDGEMENT (site) |

**Automation-boundary principle:** EC + revenue records capture only *registered* events, so unregistered mortgages, oral arrangements, GPA chains, pending suits, and physical encroachment **cannot be confirmed from any single portal** — these need cross-system correlation + human judgement. A clean EC, clean mutation, and even a **bank loan approval** are **not** title guarantees.

---

## PART 5 — AP / Telangana-Specific (current vs superseded)

### Telangana
- **Bhu Bharati (RoR in Land) Act 2024 — Act 1 of 2025, in force 14-Apr-2025 — CURRENT, replaces Dharani.** Modules 33→6; tiered grievance redressal; **Bhudhaar** number per parcel; **survey maps mandatory at registration**; physical+digital records; sada bainama regularisation; correction window to 13-Apr-2026. `bhubharati.telangana.gov.in`.
- **Dharani (2020, ILRMS)** — *superseded.* Basis: TS Rights in Land & Pattadar Pass Books Act 2020 (Act 9 of 2020). Feature: **integrated registration + automatic mutation** (Tahsildar = Joint Sub-Registrar). Failure modes drove replacement.
- **IGRS TS** (`registration.telangana.gov.in`): non-agri records from 1983; EC, market value, CC; slot booking + biometric. **22-A list & market value free online.**

### Andhra Pradesh
- **MeeBhoomi** (`meebhoomi.ap.gov.in`) over **Webland** — agri RoR (1-B, Adangal, FMB, mutation), AP RoR Act 1971; TD-cum-PPB evidentiary.
- **AP Land Titling Act 2022 (conclusive/Torrens title) — REPEALED** by AP Land Titling Repeal Act 2024 (Act 11 of 2024, ~23-Jul-2024). Meebhoomi/Webland + RoR Act 1971 remain. Statewide re-survey continues (~2027).
- **IGRS AP** (`registration.ap.gov.in`): EC, CC, market value, **prohibited-property search** (`/igrs/ppProperty`), Duty/Fee Calculator. Guideline values revised 1-Feb-2026.
- **22-A** sub-clauses (a)–(e); five categories removed Jan 2026. **NALA** AP Act 3 of 2006 (3% OTC; repeal bill Aug 2025 — verify).
- **CRDA/Amaravati** — Land Pooling Scheme (LPS): land vested in APCRDA → developed returnable plots (§126 AP CRDA Act 2014; LA R&R Act 2013 for balance).

### National digitisation frontier
- **DI-LRMP** (~98% digitised); **ULPIN/Bhu-Aadhaar** (29 states); **SAMPADA 2.0 (MP)** adds Aadhaar e-KYC, GIS, and **links digitised records with e-courts + banks to flag fraud** — the cross-system integration the BuildNow validator should mirror.

---

## ⚠️ Engineering caveats before hard-coding rules
1. **Numbers are time-versioned & recently revised** (TS guideline 1-Apr-2025; AP 1-Feb-2026; AP NALA & TS RoR laws mid-2025). **Pull live; don't hard-code rate tables.**
2. **AP sale-deed SD** appears as both a 5/6/7% slab and flat 5% — verify on live AP calculator.
3. **NALA %** (TS 5/9% vs AP 3%) partly from explainers — treat GO/portal as truth.
4. **Statutory section numbers** confirm against bare-act sources before encoding.
5. **EIA exemption law unstable** — default to "≥20,000 sq m ⇒ EIA/SEIAA."
6. **Many thresholds are state-parameterised** (fire 12 vs 15 m; TS high-rise 18 m; FSI/setbacks by road width) — per-state config, not constants.

---

*Compiled from state portals, RERA, and reputable due-diligence sources (full URL list in the research log). Not legal advice; a panel advocate should validate AP/TS-specific formats and current rates against live portals before production rule-building.*
