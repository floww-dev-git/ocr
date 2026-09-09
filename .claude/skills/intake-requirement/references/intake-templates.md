# Intake Templates — exit-ramp artifacts

Loaded only when the matching ramp fires. Real dir paths everywhere — prose module names
("the fees area") are not diffable and fail the reviewer's falsifiability doctrine.

## When a field cannot be filled (the fallback ladder)

A hole is NEVER padded. Per unmet field, in order:
1. **Derive** — fill it from evidence (Sentry trace → repro; code reading → blast radius).
2. **Ask** — one batched question round, only for what agents cannot witness.
3. **Mark** — `UNCONFIRMED` + a named consequence; proceed degraded.
4. **Redirect** — a LOAD-BEARING hole changes the ramp, never the quality bar:

| Load-bearing field | Unmet → redirect |
|---|---|
| Bug: expected vs actual | Not a bug — exit as an **investigation/spike**; re-enter classified |
| Bug: reproduction | Degrade: the failing regression test IS the repro. No failing test possible → investigation |
| Confirmed-intent (class 2) | The user's inability to confirm one sentence IS the discriminator firing → **auto-escalate to class 1** (ideation resolves the ambiguity) |
| Reclass confirmation | User may overrule the up-class — RECORD the overrule with the T-evidence; work proceeds as class 2 at explicit, logged risk |

## Confirmed-intent line (class 2 — written before the audit)
```markdown
**Intent (confirmed):** <one manager-confirmed sentence of what changes>
**Existing concept:** <owning app / PRD or ADR path if one exists>
**Candidate modules:** [validated dirs]
```
Auditing an unconfirmed interpretation is the pre-gate trap — the sentence must be the
user's confirmed words, not the manager's reading of them.

## Bug card (class 3 — the whole artifact; no PRD, no stories)
```markdown
## Bug — <slug>
**Expected:** <behaviour per spec/story — cite it if it exists>
**Actual:** <observed behaviour>
**Reproduction:** <failing input → wrong output → right output>
**Blast radius:** [real dir paths — feeds the scope-drift check at review]
**Root cause vs symptom:** <one line — what actually broke, not what surfaced>
**Trap question answered:** wrong per spec ✓ (else this is class 2 — reclassify)
**Regression test:** <path — must fail before the fix, pass after>
```

## Reclassification card (T-trigger tripped — up-classing is always a user question)
```markdown
## Reclassification — <slug>
**From → to:** class 2 → class 1
**Trigger:** T<n> — <name>
**Evidence:** <the audit finding, concretely — files/counts/edges>
**Consequence:** re-enter at ideation with this evidence; prior delta-framing is void
**User confirmed:** <date> (up-class = question; down-class = announce-and-execute)
```
One-way, once, never after tasks are cut. Save the card INTO `feature-context.md` — it is the
feature's evidence trail; an unsaved card can't back a logged-risk overrule.

## Declared-modules line (written as an ADR header line by `/create-adr`; feature-context records the ADR path; class-3 bug cards declare directly via blast-radius dirs)
```markdown
**Declared modules:** `dir/one`, `dir/two`
```
The scope fence is written where the knowledge exists: the architect declares it AT the ADR
header (Gate 2), after the Phase-B deep read — `/create-adr`'s save step writes the line (class 3 exception: the bug card's blast-radius
dirs ARE the declaration — bugs skip Phase B). Feature-lifetime declaration, not a permanent
record — it lives and dies with the feature. The scope-drift check — a hard-check item in
`/self-review-checklist` and `/review-pr` — verifies every changed path sits under the ADR's
declared set; a fix or feature touching files outside it is either mis-scoped or smuggling scope. An ADR revision or
approved scope growth re-emits this line — overwrite, never accumulate.

## Dispatch manifest (Step 10 — the `<prior-context>` payload for the A→B hinge)
```markdown
## Dispatch — <slug>
**Class:** <confirmed class> · **Route:** <ADR rail | /design-module>
**PRD:** <path, Status: Final> (class 2: confirmed-intent line inline)
**Flows:** <path to flows.md — ✓ confirmed> (class 4 with none existing: `BOOTSTRAP REQUIRED`)
**Stories:** <path> (class 4 with none existing: `BOOTSTRAP REQUIRED` — derived from the
  Step-0 parity inventory, flows ✓ then stories ◆1b, before Gate 2; see triage-classes.md
  Class-4 check)
**Candidate modules:** [validated dirs — capability-layer candidates, NOT witnessed; the
  architect's Phase-B entry read verifies them and declares the fence at the ADR]
**T-suspicions:** <anything that smelled like a T1–T6 trigger during intake — the architect
  probes these FIRST at entry> (or "none")
**Living review page:** <worktree-root path — Phase B appends its passes>
**Q&A digest:** <questions asked + user's answers, verbatim where load-bearing>
**Rejected shapes:** <shape — one-line why not, so Phase B doesn't reopen them>
**Surviving UNCONFIRMED:** <item — named consequence> (or "none")
```
The architect asking the user anything already on this manifest is a clarity-cascade failure —
report it to dhruva.
