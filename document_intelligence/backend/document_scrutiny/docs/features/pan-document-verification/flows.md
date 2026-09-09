# PAN Document Verification — Flows

## Flow 1 — attach and analyze

```
Officer picks application BN/2026/0421
  → POST /api/threads                     { application_id }              → thread
  → POST /api/threads/{tid}/documents     multipart, pan_card.pdf         → document (queued)
  → GET  /api/threads/{tid}/analyze       SSE
        step   identify running
        doc    { type_id: pan, confidence: 0.99 }
        step   identify done
        step   extract  running
        doc    { fields: { name, parentName, dob, pan } with confidences }
        step   extract  done
        step   checks   running
        doc    { checks: [ name pass, parent pass, dob pass, pan pass,
                           pan-format pass, photo pass, signature pass, hologram pass ] }
        step   checks   done
        step   verify   running
        doc    { checks: [ ..., itd_pan pass ] }
        step   verify   done
        summary { thread_status: clear, counts, open: [] }
        done
```

## Flow 2 — the seeded mismatch, resolved by an edit

```
Officer picks application BN/2026/0377
  → analyze
        name check       warn   read "MOHAMMED IRFAN SIDDIQI", application "Mohammed Irfan Siddiqui" (95.8%)
        issuer check    warn   issuer record reports nameMatch false
        summary          thread_status attention, 2 open

Officer corrects the read name
  → PATCH /api/threads/{tid}/documents/{did}/fields/name   { value: "Mohammed Irfan Siddiqui" }
        name check       pass
        issuer check    warn   (the issuer's record is unchanged by an officer edit)
        summary          thread_status attention, 1 open

Officer marks the issuer check verified by hand
  → POST /api/threads/{tid}/checks/{cid}/resolve           { action: manual }
        summary          thread_status clear, 0 open
```

## Flow 3 — the issuer does not respond

```
Officer forces the outcome from the Demo menu
  → PUT /api/threads/{tid}/service-overrides   { itd_pan: timeout }
  → analyze
        verify step runs, the adapter's timeout budget expires
        issuer check    unavailable   "No response after 3000 ms"
        summary          thread_status attention
  → POST /api/threads/{tid}/documents/{did}/retry-verification
        issuer check    pass
```

## Flow 4 — a document that is not a PAN

```
Officer attaches aadhaar_front.jpg
  → analyze
        step   identify running
        doc    { type_id: aadhaar, implemented: false, stage: identifying }
        step   identify done
        doc    { stage: done, status: attention, checks: [ supported warn ] }
        error  "Aadhaar is recognised but not supported in this build."
        summary { thread_status: attention, 1 open }
        done
```

Nothing is extracted, no field checks are produced, and no issuer call is attempted. The document is
left **finished** rather than mid-flight, carrying one warning — "Aadhaar is not supported in this
build" — so the thread settles on `attention` instead of reporting itself as still running forever.
The warning stays on the officer's worklist until they acknowledge it or mark it verified by hand.

A document nobody could classify takes the same path with its own wording:

```
        error  "We could not tell what scan_0001.pdf is. Check the scan, or attach a clearer copy."
        open   "Unknown document: Document type could not be established"
```

## Flow 5 — the scrutiny note

```
  → GET /api/threads/{tid}/note
        Scrutiny note for BN/2026/0377
        Applicant Mohammed Irfan Siddiqui, Commercial, Ground + 3, 14.8 m, survey 77/2 plot 9, Kokapet.
        Checks: 7 passed, 1 warnings, 0 failed, 0 unavailable
        Open: PAN: Income Tax PAN verification did not fully match. ...
        Recommendation: Raise shortfall for the items above before sanction
```

## Flow 6 — an Aadhaar card, verified against UIDAI

```
Officer attaches aadhaar_front.jpg on a seeded application
  → analyze
        identify   doc  { type_id: aadhaar, implemented: true }
        extract    doc  { fields: { name, dob, gender, aadhaarNo (last four shown) } }
        checks     doc  { name pass, dob pass, aadhaar-format pass }   # structure only, no Verhoeff (ADR-009 D1)
        verify     doc  { uidai pass }                                 # UIDAI confirms the demographics it was asked
        summary    thread_status clear
```

A card whose read name disagrees with UIDAI reports the department's answer per demographic: the
officer is told *which* field UIDAI disputes, not merely that something did not match (ADR-009 D2).

## Flow 7 — a driving licence, verified against Sarathi

```
Officer attaches driving_licence.pdf
  → analyze
        extract    doc  { fields: { name, dob, dlNo, validUpto, bloodGroup } }
        checks     doc  { name pass, dob pass, dl-format pass, validity pass }   # a lapsed licence warns, not fails
        verify     doc  { sarathi pass }                                          # nameMatch + dobMatch, dob null = not asked
```

## Flow 8 — a bundled sale deed and the chain of title (`BN/2026/0455`)

```
Officer attaches 01_clean_chain.pdf  (one PDF holding three registered deeds)
  → analyze
        identify   doc  { the file itself, is_bundle: true, 3 segments found }
        doc        { child deed  pp. 1-2  link_doc   1188/2003  Govind Rao → Ramesh Kumar }
        doc        { child deed  pp. 3-4  link_doc   2451/2011  Ramesh Kumar → Sunita Sharma }
        doc        { child deed  pp. 5-6  sale_deed  5820/2019  Sunita Sharma → Prakash Iyer }
        checks     the file itself: one info check "3 documents found in this file"; never sent to IGRS
                   each deed: read and checked; only the current deed compared to the applicant
        verify     the registrar is asked about each deed separately (per-deed IGRS call)
        summary    thread_status clear, documentCount 4
        chain      { verdict clean, chain.overall intact, titleDeedCount 3,
                     journey [ owner Prakash Iyer (current) ← transfer ← owner Sunita Sharma ← … ],
                     risk { level Low }  # display-only }
        done
```

The `chain` frame arrives after `summary` and before `done`: title can only be traced once every deed
in the run has been read. A PAN-only thread emits **no** `chain` frame — there is no title to trace.

The four scenario bundles trace to the verdicts they were built to produce:

```
01_clean_chain            intact   (linked, linked)   verdict clean
02_weak_transliteration   review   (linked, weak)     a buyer spelled differently in the next deed
03_gap_extent_overflow    review   (linked, gap)      a 2019 deed conveys 600 sq.yd against a 400 application
04_broken_stranger_seller broken   (linked, broken)   a 2019 vendor who was never a buyer in the chain — risk High
```

Note (ADR-010 D2): bundle 02's weakly-transliterated 2011 deed draws a name partial-match from IGRS
because the register holds the *clean* 2451/2011 — a fixture artefact. The transliteration story is
graded by the chain engine (the `weak` link), not by IGRS.

## Flow 9 — an officer correction re-traces the chain

```
Broken bundle: chain.overall broken, last link broken, risk High
  → PATCH /api/threads/{tid}/documents/{did}/fields/vendor  { value: "Sunita Sharma" }
        the flat field and the nested deed record both update (ADR-010 D4)
  → analyze  (re-trace)
        chain   { verdict clean, chain.overall intact }   # the corrected seller closes the gap
```
