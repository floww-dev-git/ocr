---
name: feature-retro
description: "Close the feedback loop at feature delivery — harvest the feature's own instruments (decision-card statuses, correction bounces, cases-vs-found, size accuracy, extension-cost claims) into 3-5 routed lessons, then retire the living review page. Dhruva-led. Use when a feature is delivered/merged, the worktree is being retired, or the user says 'feature retro', 'retrospective', 'close the feature', 'what did we learn'."
argument-hint: "[feature slug or worktree path]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Bash, Write, Edit
---

# Feature Retro

Retro for: $ARGUMENTS

The pipeline's only retrospective loop: every in-flight loop corrects the CURRENT feature;
this one asks, after delivery, **were the artifacts right?** — and feeds the answer into the
config so the NEXT feature plans better. No new bureaucracy: it reads instruments the
pipeline already wrote.

## The instruments (read, don't interview)

| Instrument | Where | What it tells |
|---|---|---|
| Decision Index statuses | the ADR | superseded cards + broken ASSUMES = decisions that didn't survive contact |
| DCP bounces | feature-context.md log + halt reports | count + ORIGIN PHASE per bounce — bounce origin = which gate is leaking |
| Cases vs found | `grep -rn "^ESCAPED-CASE:" <app>/docs/features/<slug>/reviews/` (reviewers tag misses at decision time) · scout/gamma reports | bugs found downstream that planning should have enumerated — each tag names the tasks-file + task + severity |
| Size accuracy | size tags vs how tasks actually went (session evidence, checkpoint commits) | systematic under/over-sizing |
| Scope-drift hits | scope-drift findings in review reports | fence quality — was the ADR's module list right? |
| Carried flags | tasks footers | flags that never got resolved = leaked sign-offs |
| Extension-cost deltas | grounding digests of LATER features touching this module | did "one class + one registry entry" hold? |

## Process

1. **Harvest** — read the instruments above for the feature. Facts only; no re-litigating decisions.
2. **Distill 3–5 lesson candidates, max** — each: `finding → evidence → owning agent → proposed change (memory note / rule line / skill edit / hook)`. Fewer, sharper lessons beat a laundry list.
3. **Route** — write memory notes to the owning agents' `agent-memory/` files; anything seen 2+ times across features promotes to a rule/skill/hook (dhruva's promotion ladder). Config deltas go through the normal dhruva change protocol.
4. **Final pass + retire** — append a short retro block to the living review page's `#/overview` (bounces · superseded cards · lessons), then the page retires with the worktree. Lessons OUTLIVE it in memories/rules; the page does not.

## Rules

- **Instruments over opinions** — a lesson without a file-backed finding is a hunch; park hunches in dhruva memory as "watching", never as routed lessons.
- **Blame phases, not agents** — the output is "Gate 1b leaked N flow gaps", not "the manager missed". The system gets fixed, not scolded.
- **Cheap or skipped** — a retro is ~15 minutes of reading. If a feature was trivial (class-3 bug), skip it; the dev-loop's own lessons suffice.
