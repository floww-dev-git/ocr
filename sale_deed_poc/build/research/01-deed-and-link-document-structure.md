# Indian Property Sale Deeds & the Chain of Title — A Reference for Automated Deed Extraction and Chain Validation

*Scope: national law (Transfer of Property Act 1882, Registration Act 1908, Indian Stamp Act 1899), with regional weighting toward Andhra Pradesh & Telangana (IGRS / CARD / Dharani), where the BuildNow/Urbanflow sample documents originate. Built to inform an automated deed-extraction-and-chain-validation system: every section flags **what to extract** and **why it matters for verification**.*

---

## 0. Mental model — what a deed bundle actually is

A "property file" handed to a buyer/verifier is rarely one document. It is a **bundle**:

1. The **current sale deed** (the transaction being executed/verified).
2. A stack of **link documents** (a.k.a. parent documents) — the prior registered instruments that show how each past seller themselves got the property, running back to a **mother deed** (root of title).
3. Supporting instruments — **Encumbrance Certificate (EC)**, revenue/mutation records (pahani/adangal, patta/RoR), **Index-II / certified copies**, tax receipts, plan/layout approvals.
4. Often, a **front summary sheet** ("Registration Details / Link Documents") tabulating the chain.

The deed itself is a structured legal instrument with a near-canonical clause order. The bundle, read together, is a **chain of title**. The automated system has two jobs: **(A)** parse each deed into its components, and **(B)** stitch the deeds into a chain and judge whether that chain is intact, has a gap, or is broken.

---

## 1. Anatomy of a Sale Deed (standard components, in order)

### 1.1 Title / heading & deed type
- **Contains:** the document caption — e.g. "SALE DEED", "DEED OF ABSOLUTE SALE", "CONVEYANCE DEED".
- **Why it matters:** the *nature of the instrument* determines whether and how title passes. "Sale Deed" / "Conveyance" = title-conveying. A heading like "Agreement of Sale", "General Power of Attorney", or "Development Agreement" is **not** a conveyance (see §3). **Extract the instrument type from the heading and corroborate it against the operative words — never trust the caption alone.**

### 1.2 Date & place of execution
- **Contains:** date the deed is signed and the place (town/SRO jurisdiction).
- **Why it matters:** anchors the deed in time for chronological ordering; execution date must precede registration date; place ties to the correct SRO. **Extract execution date + registration date separately** — the registration date is the legally operative one for priority.

### 1.3 Parties (Vendor / Vendee) — full descriptions
- **Contains, for each party:** full name; relation marker — **S/o**, **W/o**, **D/o**; age; occupation; full residential **address**; increasingly **PAN** and **Aadhaar**; and any **GPA holder** ("represented by his GPA holder X, vide GPA doc no NNNN/YYYY of SRO…").
- **Why it matters:** identity continuity is the backbone of the chain — **the vendor in deed *n* must be the same person who was the vendee in deed *n-1*.** Relation markers disambiguate common names and link inheritance/partition transfers. A GPA-holder signature is a **red flag** requiring the underlying GPA to be checked (post-*Suraj Lamp*, §3.4). **Extract: every party's name, role, relation chain, age, address, PAN/Aadhaar, and any "represented by GPA" clause with the GPA's document number.**

### 1.4 Recitals / "Whereas" clauses — the flow-of-title narrative
- **Contains:** the prose history of how the vendor came to own the property — "**WHEREAS** the Vendor acquired the Schedule property under registered Sale Deed bearing document no. NNNN/YYYY of SRO … dated …".
- **Why it matters:** **this is where the deed self-declares its link/parent documents.** Recitals narrate the *derivation of title* and explicitly cite prior document numbers, SROs, and dates — the single richest field for automated chain reconstruction. **Extract every cited prior-document reference (`doc-no / year`, SRO, date, instrument type) — these are the expected predecessors in the chain.**

### 1.5 Testatum & consideration / receipt clause
- **Contains:** "NOW THIS DEED WITNESSETH…"; the **consideration amount** (figures and words); the **receipt clause** (mode: cash/cheque/RTGS).
- **Why it matters:** sale *requires* consideration (TPA §54). A "sale deed" with zero/nominal consideration is suspect or is really a gift/settlement. Consideration is cross-checked against stamp-duty market value (§1.11). **Extract consideration value + payment mode + receipt acknowledgement.**

### 1.6 Operative / conveyance words (the actual transfer)
- **Contains:** "**doth hereby grant, sell, convey, transfer, assign and assure** unto the Vendee… **TO HAVE AND TO HOLD**…".
- **Why it matters:** **this is the legal act of transfer.** Their presence confirms the instrument actually conveys title. *Suraj Lamp* reaffirmed immovable property "can be transferred/conveyed only by a registered deed of conveyance." **Extract and verify presence of conveyance verbs; absence = not a title transfer.**

### 1.7 Schedule of Property — THE ANCHOR
- **Contains:** the precise legal description: **State → District → Mandal/Taluk → Village → locality**; **Survey No.** (+ sub-division / **Hissa** no.); **plot/door no.**; **extent/area** (acres-guntas for agricultural land, sq. yds/sq. ft for plots); the four **boundaries** N/S/E/W.
- **Why it matters:** **the Schedule is the property's fingerprint and the join-key of the entire chain.** Every deed must describe the *same* parcel; survey number, extent, and boundaries must reconcile deed-to-deed (allowing sub-divisions/splits). Courts treat **boundaries** as strong identifiers — where survey number/extent and boundaries conflict, boundaries often get primacy. **Extract: survey no(s)., sub-division/hissa, extent, plot/door no., village/mandal/district, and all four boundaries — and treat the Schedule as the primary entity around which deeds are matched.**

### 1.8 Habendum
- **Contains:** the "TO HAVE AND TO HOLD" clause defining the **quantum of interest** (typically absolute/freehold).
- **Why it matters:** a limited interest in the chain caps what downstream sellers could pass on. **Extract the nature/quantum of estate conveyed.**

### 1.9 Covenants, indemnity & encumbrance declaration
- **Contains:** vendor's warranties of **clear, marketable title**; that the property is **free from encumbrances/mortgages/charges/litigation/attachments**; **quiet enjoyment**; **indemnity**.
- **Why it matters:** the **encumbrance declaration** is the vendor's sworn statement of clean title; the EC corroborates it. **Extract the encumbrance/clear-title declaration and any disclosed encumbrances.**

### 1.10 Witnesses, execution, signatures / thumb impressions
- **Contains:** signatures (or **thumb impressions**) on every page; **at least two attesting witnesses**; sometimes party photos.
- **Why it matters:** execution validity; thumb impressions are common in rural AP/TS deeds and matter for identity verification. **Extract signatory blocks and witness details; flag thumb-impression execution for stronger identity checks.**

### 1.11 Stamp duty / e-stamp
- **Contains:** stamp paper / **e-stamp** certificate, stamp duty value, and the **market value** on which duty was assessed.
- **Why it matters:** insufficiently stamped instruments are **inadmissible in evidence**. Duty is charged on the higher of consideration or **government guideline value**; gross undervaluation triggers **Section 47-A** reference to the Collector. **Extract stamp/e-stamp value, market value, and any 47-A endorsement.**

### 1.12 Registration endorsement sheets — the proof of registration
- **Contains (appended by the SRO):** presentation endorsement (day/hour/place, photos + thumb impressions); **document number / year** + Book and Volume; **Book 1** (immovable-property register); **SRO name/code**, **registration date**, **Sub-Registrar's signature + seal**; on modern CARD/IGRS docs a **QR code / barcode**.
- **Why it matters:** **this block is the authoritative identity of the deed** — the `NNNN/YYYY` + SRO triple that *other* deeds cite as their link document, and what you query the EC/Index-II against. The seal + QR is the anti-forgery anchor; registration date sets priority. **Extract: document number, year, Book no., Volume/CD no., SRO name/code, registration date, seal presence, QR/barcode. This is the deed's primary key in your graph.**

> **AP/Telangana note:** under **CARD**, registration is computerized with "anywhere registration" within the state; endorsements, photos, thumb impressions and QR are system-generated. Online certified copies (Nakal) and EC (eEC) are available from IGRS AP/TS (eEC post 01-01-1983).

---

## 2. Link Documents & Chain of Title — THE CORE

### 2.1 Definitions
- **Mother deed / root of title:** the **earliest available** document establishing how ownership originated. Banks demand it before lending.
- **Link documents:** the **set of all prior registered instruments** connecting the mother deed to the present seller. Mother deed + link documents = the **Title Chain**.
- **Chain of title:** the **unbroken sequence of valid transfers** from root to current vendor. Verifying ownership = tracing the *whole* chain, not trusting the latest deed.
- **Flow of title:** the narrative of *how* title moved hand-to-hand — exactly what the recitals (§1.4) narrate.

### 2.2 How a deed references its predecessors
The machine-extractable reference tuple from the recitals:
**`{ instrument_type, document_no, year, SRO, registration_date, book_no }`** — document numbers in canonical **`NNNN/YYYY`** form, scoped by SRO. This tuple is used to *find* the predecessor deed and draw the chain edge.

### 2.3 Reconstructing the chain (the join logic)
Build a node per deed keyed by its **own** registration tuple (§1.12), then connect nodes by **three joins that must all agree**:

1. **Citation join (recital → predecessor):** the parent doc-no cited in deed *n*'s recitals equals the registration doc-no of earlier node *n-1*.
2. **Party join (identity continuity):** the **vendee** of deed *n-1* equals the **vendor** of deed *n* (name + S/o/W/o + address). For non-sale links: donor→donee (gift), settlor→settlee, deceased→heirs.
3. **Property join (Schedule continuity):** the **Schedule** (survey no., extent, boundaries) of deed *n* describes the same parcel as deed *n-1* (or a reconcilable subset after a split).

A chain is sound only when **all three joins hold at every step** from mother deed to current vendor.

### 2.4 13-year vs 30-year title search — and why
- **13-year search (practical minimum):** derives from the **12-year limitation for adverse possession** (Art. 65, Limitation Act 1963). Banks often accept ~13 years for routine lending.
- **30-year search (gold standard):** advised for high-value/complex titles because: (a) limitation against dispossession by **Government** is **30 years**; (b) a **minor** gets 3 years after majority (up to 21 years' exposure); (c) under **Evidence Act §90**, documents **30+ years** old from proper custody are presumed validly executed.
- **System implication:** parameterize the validator by **search window** (default 13y, escalate to 30y for high-value/flagged titles).

### 2.5 The "Registration Details / Link Documents" summary sheet
A tabular index sometimes attached to the front of a bundle. Typical columns: *Sl.No · Instrument type · Doc No. & Year · SRO · Registration date · Executant (From) · Claimant (To) · Extent/Schedule (Survey No., area) · Nature · Remarks.*

A formal **30-year Title Search Report (TSR)** wraps this in ~15 sections (header, property schedule, search scope, documents examined, chain-of-title narrative, EC findings, revenue records, litigation search, encumbrances, defects, opinion, advocate's certificate, annexures).

> **System implication:** if a summary sheet exists, treat it as a *claimed* chain to be **verified against the actual deeds**, not as ground truth — generate the chain independently and reconcile. (It is metadata, **not** a conveyance — exclude it from the chain as a deed node.)

### 2.6 Aggregating multiple parcels (one buyer, several sellers)
A buyer assembling a larger holding produces a **fan-in**: multiple independent sub-chains (one per source parcel/seller), each with its own mother deed, converging on the buyer. To validate:
- Maintain a **separate chain per source parcel** (keyed by survey no./sub-division).
- **Reconcile extents:** the sum of constituent extents must equal the aggregated extent in the new deed's Schedule. Mismatch = over/under-counted, double-sold, or overlapping boundaries.
- Internal boundaries should knit together; the outer boundary of the aggregate should match the union.

### 2.7 Intact vs Broken vs Gap

| State | Definition | Detectable signals |
|---|---|---|
| **INTACT** | Every transfer from mother deed to current vendor is valid/registered; party identity, Schedule, and recital citations reconcile at each step; EC corroborates; no time gaps. | Continuous `vendee(n-1)=vendor(n)`; recital citations resolve; extents/boundaries reconcile; EC shows each transaction. |
| **GAP (missing intermediate deed)** | A predecessor is *referenced* but absent/unlocatable; or an unexplained period where the property must have changed hands. | A cited link doc-no with no matching node; unexplained period; EC shows a transaction the bundle lacks. **Often curable** via certified copy / EC. |
| **BROKEN** | Genuine failure: identity discontinuity, unexplained mutation jump, reliance on a non-conveying instrument (GPA "sale", unprobated will), forged endorsement, double sale, or irreconcilable extent/boundary. | `vendor(n)≠vendee(n-1)`; mutation without a deed; a "sale" resting on GPA/agreement; conflicting transfers in EC; survey/extent that can't reconcile. **Defeats title.** |

---

## 3. Types of title-affecting instruments — what conveys, what doesn't

| Instrument | Consideration | Transfers title? | Notes for the validator |
|---|---|---|---|
| **Sale Deed / Conveyance** | Price | **Yes — full** | Strongest link. Needs registration + operative conveyance words + consideration. |
| **Gift Deed** | None (love/affection) | **Yes — immediate & absolute** on acceptance; must be registered | Verify acceptance + donor's title. |
| **Partition Deed** | None (division) | **Yes** — converts joint holding into separate ownership | Verify *all* co-sharers are parties and shares/extents reconcile. |
| **Settlement Deed** | "love/affection" | **Yes** when vesting is immediate; registered | *N.P. Saseendran v. Ponnamma* (2025): immediate vesting = gift/settlement; deferred-till-death = will. |
| **Release / Relinquishment** | with/without | **Yes — only among co-owners** | A "release" by a stranger conveys nothing. |
| **Will** | n/a | **Only on death**; often needs **probate** | **Weak/contingent link** — corroborate with mutation + probate. |
| **Inheritance / intestate** | n/a | **By operation of law** on death | Evidenced by death certificate + legal-heir + mutation, not a deed. A mutation jump with no succession proof = gap/broken. |
| **Court Decree / Sale Certificate** | varies | **Yes — by operation of law** | Verify decree is genuine/final, not under appeal. |
| **GPA (General Power of Attorney)** | n/a | **NO** — only agency | **Critical red flag — §3.4.** |
| **Agreement of Sale (ATS)** | earnest money | **NO** — contract to sell in future | Not a link. |
| **Development Agreement / JDA cum GPA** | area/revenue share | **NO transfer of land title** | §3.5. Authority to develop + execute deeds for owner; not a conveyance. |

### 3.4 *Suraj Lamp* (SC, 11 Oct 2011) — why "GPA sales" don't transfer title
- There **cannot** be a transfer of immovable property by a **Power of Attorney**, **Agreement of Sale**, **Will**, or the combined **"SA/GPA/WILL"** transaction.
- **"Immovable property can be legally and lawfully transferred/conveyed only by a registered deed of conveyance."**
- Even an **irrevocable GPA does not by itself transfer title**; title passes only when the attorney **executes a registered sale deed** on the principal's behalf.
- **System implication:** if any link *rests on* a GPA/agreement/will as the conveyance, flag as **likely broken**. A GPA as the *authority* under which a registered sale deed was executed is acceptable — but the GPA must be **registered, valid, unrevoked at execution**, and the underlying owner's title verified.

### 3.5 Development Agreement cum GPA (JDA-GPA) — AP/Telangana relevance (BuildNow)
- Landowner + builder sign a **registered JDA** (+ a registered **GPA** empowering the builder to execute sale deeds for the owner's buyers).
- **Neither the JDA nor the GPA transfers the land title** — ownership stays with the landowner until individual registered sale/conveyance deeds are executed. Flat buyers' title flows *from the landowner*, via the builder-as-GPA.
- **System implication:** expect a node = "JDA cum GPA" that is *authority, not conveyance*; the real title link to each buyer is the **registered sale/conveyance deed** executed under it.

---

## 4. Registration & document mechanics

- **Index-II / Suchi-2:** a one-page SRO abstract of a registered immovable-property document (doc no./year, SRO, nature, parties, consideration & market value, property description, registration date) — a public, queryable summary for independent chain verification.
- **Certified copies (Nakal):** SRO-attested true copies; in AP/TS downloadable online via IGRS for newer records; useful to **fill gaps** (retrieve a referenced-but-missing link document).
- **Document numbering & books:** **Book 1** = non-testamentary documents affecting immovable property (sale/gift/partition/settlement/mortgage). Document number is **unique per SRO per year** → `doc-no / year + SRO` is the global key. CARD/IGRS add Volume/CD + QR.
- **Encumbrance Certificate (EC/eEC):** lists all registered transactions (sales, mortgages, charges, attachments) over a period — the corroborating ledger. IGRS AP eEC covers post 01-01-1983 online. Searchable by document number, survey number, or house number, scoped by district + SRO + period. "Nil EC" means no *registered* encumbrance — necessary, not sufficient (misses unregistered claims).
- **AP vs TS:** **CARD** (since 4 Nov 1998) computerized registration across undivided AP ("anywhere registration"). **Telangana Dharani** (29-10-2020) integrates land-records + registration; for agricultural land, **registration and mutation happen together** (less registration/revenue mismatch). **AP** retains conventional SRO registration (CARD) + separate revenue records (RoR/adangal, Webland) — so registration-vs-mutation reconciliation matters more in AP.

---

## 5. Implications for an automated validator

### 5.1 Fields the system MUST extract per deed
- **Identity / registration (primary key):** document no., year, SRO, Book no., Volume/CD, registration date, seal present, QR present.
- **Instrument:** deed type (heading **and** operative words), execution date, place.
- **Parties:** name, role, relation (S/o, W/o, D/o), age, address, PAN, Aadhaar; **"represented by GPA"** flag + GPA doc no./year/SRO.
- **Recital references:** list of `{instrument_type, doc_no, year, SRO, date, book}` cited in "Whereas" clauses.
- **Consideration:** amount (figures+words), payment mode, receipt.
- **Conveyance words:** presence of sell/convey/transfer; habendum estate type.
- **Schedule (the anchor):** state/district/mandal/village/locality, survey no. + sub-division/hissa, plot/door no., extent (normalized), all four boundaries.
- **Encumbrance declaration; stamp (value, guideline value, §47-A); execution (signatures/thumb, witnesses).**

### 5.2 Derived/joined entities
- **Property node** keyed by normalized survey-no + sub-division + village (the Schedule fingerprint).
- **Person nodes** keyed by name + relation + address (fuzzy, S/o disambiguation).
- **Chain edges** = (party join) ∧ (citation join) ∧ (property join) between consecutive deeds.
- **Extent ledger** per property to reconcile splits/aggregations (sum of children = parent).

### 5.3 Signals of a CLEAN chain
- Continuous identity `vendee(n-1)==vendor(n)`; every recital citation resolves; Schedule survey-no/extent/boundaries reconcile; aggregations sum correctly; every transfer appears in the EC; all conveyances are registered Book-1 deeds with intact seal/QR; search window satisfied; stamp ≥ guideline value (no open §47-A).

### 5.4 Signals of a PROBLEMATIC chain (flag / escalate / block)
- **Identity discontinuity** (broken) · **dangling citation** (gap) · **mutation jump** with no registered deed (broken) · **non-conveying instrument used as a link** — GPA/Agreement/unprobated Will (*Suraj Lamp* → broken) · **GPA-executed sale** with unregistered/revoked GPA or unverified principal title · **JDA-GPA mistaken for conveyance** · **Schedule mismatch** / extents that don't sum · **endorsement anomalies** (missing/forged seal, absent QR, over-written doc no., EC contradiction) · **stamp/valuation defect** · **limitation exposure** (chain too short; minor/government interest unresolved; will-root without probate).

### 5.5 Design principles (aligned to repo engineering rules)
- **Deterministic safety gates stay code-owned**: the GPA/*Suraj-Lamp* check, identity-continuity, extent reconciliation, endorsement/QR verification are **rule-based** — a better model lowers OCR error rate but never makes these optional.
- **Fail in the safe direction:** ambiguous joins (fuzzy name, illegible survey no.) → **flag for human review**, don't silently pass.
- **The Schedule is the join key, the registration tuple is the primary key, the recitals are the edge list.**

---

## Sources
See the research log; key primary sources to read in full before production rule-building: TPA 1882 §§54/122, Registration Act 1908, Limitation Act 1963 Art. 65, Evidence Act §90, Stamp Act §47-A, and *Suraj Lamp & Industries (P) Ltd. (II) v. State of Haryana* (SC, 2011, indiankanoon.org/doc/1565619). AP/TS portals: registration.ap.gov.in, registration.telangana.gov.in. A panel advocate should validate AP/TS-specific record formats against actual sample bundles.

*Compiled from secondary legal explainers + primary statute/portal sources. Not legal advice.*
