Objective:
I am implemented the prototype of the document intelligence. Now i want to implement this.


Implement this following
1. Fronted - React
2. Desgin System - ShadCN
3. Backend - Django

Already i am already implemented similar poc in this repo it is sale_deed_poc. 
Create another poc in this repo in this poc we will integrate all types of document verification.

First we will implement the PAN only. 
1. You can mock external services to mimick.
2. Follow the Prototype and inspire from that implement the pan. PROTOTYPE:- index.html


Direction
1. In the reference prototype, keep as it of the mock applications, here we implement the PAN verification only.


--------------------------------------------------------------------------------------------------------------------------------


# A. Document identification (what we can recognize)
1. Type classification
2. Bundle segmentation
3. Document quality assessment


# B. Extraction (what we can read off a document)
1. Field extraction
2. Signature / photo / seal / QR / hologram detection
3. QR / barcode decoding — read the embedded data and compare it to the printed text (Aadhaar QR, e-PAN QR, registration QR).
4. Confidence + provenance — every field carries a confidence score and a bounding box pointing to where it was read.


# C. Checks (what we can verify)

#### Intrinsic (document alone):

1. Format/checksum validation — PAN pattern, Aadhaar Verhoeff checksum, GSTIN, IFSC, licence-number grammar.
2. Internal consistency — DOB vs age stated elsewhere; extent in sq.yd vs sq.m; amount in figures vs words; dates in logical order.
3. Validity/expiry window — is it still in force on the scrutiny date; expiring-soon warning.


#### Cross-document (this doc vs the application, or vs other docs):
1. Field-match against the application — name, DOB, survey no., plot, village, extent (exact, fuzzy, tolerance-based).
2. Cross-document consistency — the name on the PAN vs the Aadhaar vs the deed vs the application, all reconciled.
3. Chain-of-title reasoning — ownership flows correctly seller→buyer across a stack of deeds; gaps and breaks flagged.


#### Extrinsic (against an external authority):
1. Issuer verification — confirm the document against the issuing department's record (UIDAI, Income Tax, Sarathi, IGRS, Dharani, RDO).

# Policy / rules:
1. Applicability rules — which documents this application actually needs (height > 15 m → fire NOC, near water body → irrigation NOC).
2. Eligibility / regulatory rules — setbacks, road width, land-use, floor limits against the by-laws.

# Outcomes / actions (what we produce)
2. Per-document status (verified / needs a look / could not verify / failed).
