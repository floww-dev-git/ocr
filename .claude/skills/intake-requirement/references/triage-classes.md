# Triage Classes — Step 4 Reference

Loaded only at triage. Four classes, no more — a class earns existence only if it changes
downstream artifacts or gates. Config/ops changes and spikes exit before the rail entirely.

## The boarding table

| Class | After triage, boards at | Phase-B depth (architect, at phase entry) | Minimal WHAT-artifact | Gates |
|---|---|---|---|---|
| **1 · new concept** | Step 5 (ideation — full rail) | FULL deep read: per-module delta + edges + debt; **T1–T6 ledger** | PRD (broad: JTBD · value prop · candidates) + flows ✓ + stories citing flow steps | ◆1a (PRD) → ✓ flows → ◆1b (stories) |
| **2 · update** *(majority lane)* | Step 8 (flows-patch) → delta-stories at Step 9 | DELTA read: modules + {extend / new-sub} + edges; **T1–T6 ledger** | delta-stories citing flow steps + canonical `flows.md` patched same pass | ◆1b only (no new PRD → no 1a) |
| **3 · bug fix** | bug lane — exits at Step 4 | none — never enters Phase B; blast-radius dirs declared in the bug card | repro · expected-vs-actual · root-cause-vs-symptom line · regression test (fails-before/passes-after) | commit gate only |
| **4 · refactor / debt** | Step 10 (dispatch straight to Phase B — `/design-module`) | FULL **two-sided**: before→after module graph (new · updated · absorbed/retired) + parity inventory (= `/design-module` Step 0) | structure delta + behavior-preserving declaration + canonical flows/stories (existing, patched — or bootstrapped from the parity inventory; see Class-4 check below) | ✓ flows + ◆1b when bootstrapping (post-inventory), then Gate 2 (ADR) |

Depth is billed to Phase B for every lane — Phase A never reads code. The declared-modules
scope fence is written by the architect AT the ADR (Gate 2); class 3's bug card is the only
intake-time declaration (bugs skip Phase B, so the fence must exist before the fix).

## The Class-4 flows & stories check (user ruling 2026-07-04, REF-001)

A refactor preserves behaviour — but the behaviour must be WRITTEN somewhere to be preserved
against. At the class-4 exit, check whether the canonical artifacts for the behaviour under
refactor exist: `<owning_app>/docs/features/<slug>/flows.md` + the epic story file(s) at `<owning_app>/docs/user_stories/<epic-slug>.md`.

- **Present** → patch mode, exactly as class 2 (usually a no-op — behaviour-preserving means no
  journey changes). Attach both paths to the dispatch manifest as the parity baseline.
- **Absent** → mark **bootstrap required** on the dispatch manifest and dispatch as usual.
  Sequencing (the REF-001 order): the architect's `/design-module` Step-0 parity inventory runs
  FIRST — it is the ground truth of current behaviour, and Phase A never reads code — then the
  manager derives bootstrap flows (✓ checkpoint) and stories (Gate 1b) FROM that inventory.
  Gate 2 (ADR) does not close until the bootstrapped stories are approved — the slices'
  integration suites and the parity declaration need stories to trace to.

## Performance work — which class?
Ask: **"Is a stated expectation (SLA, timeout, capacity) being violated?"** Yes → **class 3**
(wrong per spec; the regression test is the benchmark — fails before, passes after). No — same
behaviour, better speed/structure → **class 4** (behaviour-preserving declaration; parity
framing). Perf work is never class 2: nothing about the WHAT changes, so there are no
delta-stories to write.

## The 1-vs-2 discriminator
Ask: **"Is there more than one plausible product shape for this?"**
- One obvious shape → class 2 (delta-stories, no ideation).
- Competing shapes, new actors, a new flow, or changed invariants → class 1 wearing an update
  costume. When unsure, ask the user — never default silently (pre-gate interpretations are
  questions, per `consent-granularity.md`).

## The bug-lane trap question
Before any class-3 exit: **"Is the behaviour wrong per spec, or is the spec changing?"**
The second answer reclassifies into class 2 — an extension in disguise needs stories, not a
patch. Skipping this question is how spec-changes smuggle past Gate 1 as "bug fixes."
Mechanical backstop: a fix touching files outside the declared blast radius means the root
cause lives elsewhere (re-audit) or a spec-change is riding the bug lane.

## Escalation (class 2 → class 1): the T-triggers

Six triggers — T1 homing failure · T2 rule-of-three · T3 edge novelty · T4 unabsorbed axis ·
T5 parity gap · T6 contract break. **Definitions and check procedures live with their runner:**
`.claude/rules/references/t-triggers.md` — the architect executes them at **Phase-B entry**
(the first deep read); the manager only consumes the verdict, delivered back through the
Design Correction Protocol (`dev-loop.md`).

The escalation *protocol* (manager-owned): any trip → reclassification card → **user confirms**
(up-classing is always a question) → re-enter Phase A at ideation WITH the evidence. One-way,
once, never after tasks are cut.
