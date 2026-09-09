# Context-Budget Audit — Always-On Surface

**Status:** PROPOSAL (no edits made). Manager gates with user before any execution.
**Date:** 2026-07-09 · **Author:** dhruva · **Trigger:** session-optimization #10, at REF-001 S2 clean boundary.

---

## 0. Headline — read this first

**Mechanism VERIFIED against the installed binary (Claude Code v2.1.205, 2026-07-09). Both uncertainties resolved — no mechanism bug. `globs:` works; references are not always-on. The plan is content-trims only.**

Initial doubt (now settled): current official docs say the path-scope key is `paths:`, and this repo's 10 scoped rules use `globs:`. I disassembled the installed binary rather than trust docs-vs-memory:

- **U1 — `globs:` IS the honored key for `.claude/rules/`.** The loader filters rules by a `.globs` field: `i.filter((l)=>{if(!l.globs||l.globs.length===0)return!1; …})` and activation reason `i.globs?"path_glob_match":…`. The `paths:` in the docs is the **skills** conditional-activation field ("Glob patterns"), a different surface — the guide/docs conflated them. **My 2026-03 memory was right. Do NOT rename `globs:`→`paths:` — it would break scoping.** The 696 lines of scoped rules are genuinely NOT always-on.
- **U2 — `references/*.md` are NOT always-on.** The binary's own help names the auto-load set: `` `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md` `` — a **flat** `*.md` glob, so the `references/` subdir is excluded. No top-level rule `@`-imports a reference either (verified). The load-on-demand design works as intended.

Net: the two "jackpot" moves I had gated on this test (globs→paths rename, references relocation) are **VOID** — good that they were gated, not executed. The real, safe win is the content trim: **686 → ~388 always-on rule-lines (−43%)**, under the <500 target.

---

## 1. Measured baseline (always-on surface)

### 1a. Top-level rules — the always-on candidates

Always-on = no path-scoping frontmatter. 13 files, **686 lines** (matches the brief):

| file | lines | chars |
|---|---|---|
| dev-loop.md | 179 | 17,264 |
| agent-delegation.md | 112 | 9,285 |
| consent-granularity.md | 79 | 5,554 |
| explanation-format.md | 57 | 4,721 |
| clean-code.md | 51 | 5,872 |
| agent-interaction.md | 45 | 5,057 |
| model-routing.md | 43 | 2,477 |
| exception-handling.md | 41 | 1,846 |
| worktree-workflow.md | 34 | 1,615 |
| interactive-questions.md | 31 | 1,580 |
| investigate-before-answering.md | 8 | 684 |
| day-plan.md | 3 | 231 |
| ai-readiness-gate.md | 3 | 300 |
| **always-on total** | **686** | **~56.5k** |

### 1b. Path-scoped rules — 696 lines, confirmed NOT always-on

10 files keyed `globs:` (the correct rules key — see §2): graphql.md 104 · clean-architecture.md 99 · configio-architecture.md 91 · testing.md 89 · storages.md 73 · config-delegation.md 69 · models.md 53 · interactors.md 53 · feature-context.md 43 · rich-domain-models.md 22. **Total 696 lines.** Load only when a file matching their glob is read. Correctly scoped — leave as-is (this is the model to follow).

### 1c. references/ — 620 lines, confirmed NOT always-on

agent-teams-pipeline 183 · engineering-canon 115 · module-map 84 · t-triggers 68 · fixture-doctrine 65 · phase-b-entry 56 · feature-folder 49. **Total 620 lines.** In a subdir the flat `.claude/rules/*.md` scan skips; load-on-demand via loader/Read. Working as designed.

**Confirmed baseline: 686 always-on rule-lines** (the 13 top-level no-`globs:` rules). Plus root CLAUDE.md (75) and the ancestor `Workspace/CLAUDE.md` leak (~50, flagged separately in dhruva memory) — those are CLAUDE.md always-on, out of rules-trim scope.

---

## 2. Mechanism verification — DONE (binary disassembly, authoritative)

Resolved by inspecting the installed binary (`/Users/veronica/.local/share/claude/versions/2.1.205`), not a live-session probe (a subagent loads the whole tree and can't distinguish cases; the binary is definitive):

| Q | Result | Evidence (binary strings) |
|---|---|---|
| **U1** `globs:` honored for rules? | **YES** | rule filter `if(!l.globs||l.globs.length===0)return!1`; bucket split `filter((T)=>o?T.globs:!T.globs)`; activation `i.globs?"path_glob_match":…` |
| `paths:` = the rules key? | **NO** — it's the **skills** conditional field | `paths:aJe().optional().describe("Glob patterns…")` under conditionalSkills |
| **U2** references/ always-on? | **NO** — flat scan excludes subdir | help text: auto-load set = `` `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md` `` (flat `*.md`) |
| any `@`-import pulling references in? | **NO** | grep of all top-level rules + CLAUDE.md — none |

**Consequence:** baseline is confirmed 686 always-on rule-lines (Scenario A). No rename, no relocation. Proceed to §3 content trims only.

---

## 3. Per-file verdicts — the 13 always-on rules (valid regardless of U1/U2)

| file | lines | bucket | proposed change | Δ always-on | risk |
|---|---|---|---|---|---|
| **clean-code.md** | 51 | → path-scope | `paths: ["**/*.py"]` | −51 | **Low** — code-authoring only; hard limits also hook-backstopped (`quality-gate.sh`). Loads whenever any `.py` is read = exactly when needed. |
| **exception-handling.md** | 41 | → path-scope | `paths: ["**/*.py"]` | −41 | **Low** — same as above; bare-except/generic-except also hook-enforced. |
| **explanation-format.md** | 57 | → load-on-demand | 4-line always-on stub ("on 'explain this code' → load `references/explanation-format.md`") + move body to references | −53 | **Low** — trigger is an explicit user ask, easy to catch on a stub. |
| **model-routing.md** | 43 | → load-on-demand | 4-line stub + `references/model-routing.md`; loaders = `/task-breakdown` (tag step) + task-coordinator (spawn step) | −39 | **Low-Med** — a miss mis-routes model *tier* (a cost delta, not a correctness bug); the "when in doubt → frontier" default is self-correcting. Keep the floor rule (consequence-bearing paths) in the stub. |
| **dev-loop.md** | 179 | → spine + reference | keep ~85-line spine always-on (stage list, 4 gates, Commit-Frequently-Gate-Once rules, exit criteria). **HARD CONSTRAINT: the 4-gate enumeration MUST land in the SPINE, never the load-on-demand reference** — after the 2026-07-10 trim, `agent-delegation.md` points here for the gates instead of restating them, so dev-loop.md is their only always-on home. Move **Design Correction Protocol** (who-does-what tables, two Phase-B lanes, anti-patterns ~90L) to `references/dev-loop-corrections.md`, loaded when a plan-artifact-wrong is detected | −94 | **Medium — do LAST, carefully.** The correction protocol must load the instant a developer hits a wrong plan. Mitigate with a 3-line stub in the spine ("plan wrong mid-impl → HALT, load `references/dev-loop-corrections.md`, do not work around"). The HALT trigger is the load trigger. |
| **agent-delegation.md** | 112 | MUST-stay (trim prose) | keep all 3 routing tables + domain boundaries + pre-impl gate (every-turn routing, complete-or-broken); compress the prose sections that duplicate dev-loop.md (Design Correction Routing, Pipeline Continuation detail already point to `references/agent-teams-pipeline.md`) | −~20 | **Low-Med** — never touch the routing tables; trim only prose. |
| **consent-granularity.md** | 79 | MUST-stay | keep; optional −10 by tightening the two worked examples | −0 (−10 opt) | governs every gate/sub-decision, path-independent. |
| **agent-interaction.md** | 45 | MUST-stay | keep | 0 | how every agent presents to the user, every turn. |
| **worktree-workflow.md** | 34 | MUST-stay | keep | 0 | branch/context-resumption process; not file-scopable. |
| **interactive-questions.md** | 31 | MUST-stay | keep | 0 | HOW to ask (AskUserQuestion vs text), every gate. |
| **investigate-before-answering.md** | 8 | MUST-stay | keep | 0 | tiny, universal. |
| **day-plan.md** | 3 | MUST-stay | keep (already the thin-stub model) | 0 | already ideal. |
| **ai-readiness-gate.md** | 3 | MUST-stay | keep (already thin stub) | 0 | already ideal. |

**Content-trim subtotal: −298 lines** (−318 with the two optional prose trims). No decision-critical rule leaves always-on; every moved rule keeps a stub at its load-trigger point.

---

## 4. Projected after (mechanism confirmed — single scenario)

- Always-on rule-lines: **686 → ~388** (**−43%**), under the <500 target for the first time.
- Per-turn main-session saving ≈ 298 lines re-billed on every turn of the longest-lived session (depth-0 manager) — the stated #1 token sink.
- No mechanism fixes needed (globs works, references already off the always-on path). The prior draft's "Scenario B jackpot" (globs→paths rename, references relocation) is **VOID** — the binary check disproved the premise. Content trims in §3 are the whole plan.

---

## 5. CLAUDE.md litmus pass (flag + estimate only — NOT always-on, load per-app-touch)

App-**root** CLAUDE.mds over the 80-line target (config-delegation.md standard):

| file | lines | over | trim estimate |
|---|---|---|---|
| **payments_engine/CLAUDE.md** | **348** | **over 250 HARD limit** | the gold-standard-for-quality file is 40% over the hard cap — biggest litmus violation. ~−120 to reach 230; ~−268 to hit target. Likely carries file-by-file detail that violates the anti-pattern guide. |
| sales_crm_core/CLAUDE.md | 114 | +34 | ~−35 |
| fee_engine/CLAUDE.md | 113 | +33 | ~−33 |
| licenses/CLAUDE.md | 112 | +32 | ~−32 |
| tdr/CLAUDE.md | 97 | +17 | ~−17 |
| jobs_engine/CLAUDE.md | 93 | +13 | ~−13 |
| rules_engine/CLAUDE.md | 92 | +12 | ~−12 |
| ib_payments · iam · bps | 87 each | +7 | ~−7 each |
| ib_collections/CLAUDE.md | 82 | +2 | trivial |

Subfolder CLAUDE.mds over their 100-line hard limit: `bps/configio/core/io_engine` (116), `bps/models` (112). Both should be checked against the 20-line-non-obvious threshold.

**Recommendation:** treat payments_engine as its own trim task (it's over the hard limit and is the template others copy — fixing it fixes the exemplar). The 80–114 cluster is a lower-priority litmus sweep, one `/write-app-claude-md` pass each. Do NOT rewrite in this audit — flagged only, as instructed.

---

## 6. Execution order (safest-first)

Mechanism check already done (§2) — no rename/relocation steps. **Important: use `globs:`, never `paths:`, for any new scoping (the binary proves `globs:` is the rules key).**

1. **Path-scope clean-code.md + exception-handling.md** — add `globs: ["**/*.py"]` frontmatter. Zero content change, hook-backstopped. **Low risk.** (−92)
2. **Load-on-demand: explanation-format.md, then model-routing.md** — 4-line always-on stub + move body to `references/`. **Low / Low-Med.** (−92)
3. **agent-delegation.md prose trim** — routing tables untouched, compress prose that duplicates dev-loop.md. **Low-Med.** (−20)
4. **dev-loop.md spine/reference split — LAST, with care.** Keep the HALT-trigger stub; verify a wrong-plan scenario still surfaces the correction protocol. **Medium.** (−94)
5. Separate follow-up: **payments_engine/CLAUDE.md** trim (over the 250 hard limit).

**Cache-stability:** batch steps 1–4 into ONE commit wave (companion optimization #9) at this clean REF-001 boundary — don't dribble config edits and bust the prompt cache repeatedly.

**Cache-stability note:** batch steps 2–7 into ONE commit wave (companion optimization #9). Dribbling config edits busts the prompt cache repeatedly; one deliberate pass at this clean REF-001 boundary is the correct cadence.

---

## Appendix — mechanism sources (resolved)
- **Authoritative: installed binary v2.1.205.** `.claude/rules/` path-scoping key = **`globs:`** (rule filter `if(!l.globs||l.globs.length===0)return!1`). Auto-load set = `CLAUDE.md` · `.claude/CLAUDE.md` · `.claude/rules/*.md` (flat). `paths:` is the **skills** conditional-activation field, not rules.
- Docs / claude-code-guide (2026-07-09) said `paths:` is the native key — **wrong for rules** (conflated with the skills surface). Lesson: for undocumented-vs-documented frontmatter conflicts, disassemble the binary; don't arbitrate docs-vs-memory.
- dhruva memory 2026-03-27 (`globs:` is the working key) — **CONFIRMED correct** by the binary. Memory updated to cite the binary evidence + the docs trap.
- Non-fork subagents load the entire memory hierarchy, so a subagent sees every rule + reference regardless of scoping — which is why the live-session probe was inconclusive and the binary was the right tool.
