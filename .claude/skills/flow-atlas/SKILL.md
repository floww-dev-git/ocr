---
name: flow-atlas
description: Generate an interactive Flow Atlas HTML document for any module (tasks, tdr, automations, fees…) — a Schema constellation of its tables plus an animated Story of one real lifecycle. User supplies only tables + critical columns, critical cases, and user flows; the skill owns ALL UI/UX (theme, fonts, icons, layout, popovers, animations, scenes). Use when the user says "flow atlas", "build the atlas for <module>", "interactive schema doc", "animated module documentation", or "make the html doc like fee-payments-atlas".
argument-hint: "[module name and owning app, e.g. \"tdr, tdr/\"]"
disable-model-invocation: false
allowed-tools: Read, Grep, Glob, Edit, Write, Bash
---

# Flow Atlas Generator

Produces a self-contained HTML doc at `<owning_app>/docs/<module>-atlas.html`, identical in look & behavior to the canonical `fee_engine/docs/fee-payments-atlas.html`. The design is FROZEN — you author data, never styles.

## What the user gives you (ask for gaps, in ONE message)

| Input | Example |
|---|---|
| Module + owning app | "TDR", `tdr/` |
| Core tables + critical columns | model names or "read the models" |
| Critical cases / gotchas | "balance can go negative", "deprecated col X" |
| User flows | "officer issues certificate → citizen applies → …" |

Everything else — layout, icons, colors, scene pacing, popovers, animations — is YOURS via the template. Never ask the user about visuals.

## Hard rules

1. **Verify before rendering** — every column, enum value, and status transition MUST be read from `models/`, `constants/enum.py`, and (if present) `tech_docs/` before it appears in the doc. Code beats docs for enum names; docs beat memory for semantics.
2. **Real example data only** — one concrete story instance with realistic ids, names, amounts, timestamps. Never `foo`, never lorem.
3. **Confusable columns get contrast popovers** — if a table has 2+ similar columns (multiple amounts, multiple statuses, multiple dates), each gets a FIELD_INFO popover explaining its purpose AGAINST the others. Deprecated columns get `dep:true` + a "don't build new logic on this" warn.
4. **Do not restyle** — no new colors, fonts, or component variants. Tokens and components are fixed (see `references/design-system.md`). Only DATA blocks change.

## Process

1. **Gather + verify.** Read the module's models, constants, CLAUDE.md, tech_docs. Build your fact base: tables, columns, enums (exact values), FK vs string references, lifecycle/state machines, the flow's actors.
2. **Copy the template.** `cp references/template.html <owning_app>/docs/<module>-atlas.html`. The template is the fee/payments atlas with `@DATA:` markers — its content doubles as a worked example.
3. **Replace the 10 data blocks** (search for `@DATA:` markers; full specs in `references/authoring-guide.md`):
   - `@DATA:BRAND` — `<title>`, topbar crumb, sidebar tooltip sublabels, footer provenance line.
   - `@DATA:HERO` — two-tone headline (domain word amber `.fe`, outcome word green `.ok`), 13px lede, CTA label.
   - `@DATA:NODES` / `@DATA:EDGES` — schema constellation (positioning math in guide).
   - `@DATA:FIELD_ENUMS` / `@DATA:FIELD_INFO` — column popovers.
   - `@DATA:CHIP` — status → chip-color map for every status value used anywhere.
   - `@DATA:TABLES` — story deck mini-table configs.
   - `@DATA:FLOW` — flow-chart nodes (one per scene, actor badges for humans/externals).
   - `@DATA:SCENES` — the animated story beats.
4. **QA gate** (all mandatory):
   - `node --check` the extracted `<script>` block.
   - `grep` the output for leftover source-module strings (`fee_engine`, `Ravi`, `efr_`, `ord_7c` …) — zero hits unless your module is fees.
   - Every `FIELD_ENUMS`/`FIELD_INFO` key matches a displayed `node.field` name exactly (popover unreachable otherwise).
   - Every status value in SCENES exists in `CHIP`; every scene has a FLOW node; every beat's table key exists in `TABLES`.
   - Node overlap check: for each column of nodes, `y + 30 + rows*19 + 8 + 20 ≤ next node's y`; grow the canvas (3 constants: viewBox, dotgrid rect, applyZoom) if needed.
   - Open-in-browser sanity: both tabs render, play runs end-to-end, popovers appear, fullscreen works.
5. **Deliver.** Report the file path; remind that fonts load from Google Fonts (offline → system fallback). Do NOT publish to an artifact unless asked.

## References

- `references/template.html` — the frozen engine + worked example (fee/payments). COPY, never edit in place.
- `references/authoring-guide.md` — per-block authoring specs: beat vocabulary, icon library, positioning math, popover copy rules, chip mapping rules.
- `references/design-system.md` — tokens & component inventory (context for judgment calls; not a license to restyle).
