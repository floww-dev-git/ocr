# Flow Atlas — Data Block Authoring Guide

Every block lives in `template.html` behind a `@DATA:` marker. The fee/payments data already there is the worked example — replace it, matching its shape exactly.

## Page anatomy (fixed)

```
sidebar rail (₹-style logo, 2 icons) │ topbar (crumb + boundary chip)
                                      │ hero band (two-tone h1, lede, CTA, 2 pill tabs)
                                      │ ┌─ Tab SCHEMA: constellation (zoom, fullscreen, popovers)
                                      │ └─ Tab STORY: flow-chart film → controls → table-writes deck
```

## @DATA:BRAND + @DATA:HERO

- `<title>`: `<Domain A> × <Domain B> — <outcome phrase>`.
- Topbar crumb: module name + `small` subline naming the apps.
- Boundary chip: the ONE invariant a reader must never forget (fees: `paise = int(rupees × 100)`; pick your module's equivalent — e.g. tdr: `area is never destroyed, only transferred`). Keep the small rupee/domain icon only if money-related.
- H1 formula: `<verb the domain> <span class="fe">from X</span> to <span class="ok">TERMINAL_STATE</span>` — amber for the origin concept, **green for the successful terminal state**.
- Lede: ≤2 sentences, bold the app names, end with "told through the actual tables, one row at a time."
- CTA: always `Play the story`.

## @DATA:NODES / @DATA:EDGES — schema constellation

Node: `{id, label, app:'fe'|'pe'|'jn', x, y, w, fields:[[name, badge|null, type]]}`.

- `app` = hue: `fe` amber (domain A), `pe` blue (domain B), `jn` violet (junctions/audit/logs). Single-domain module: primary entities `fe`, runtime/derived `pe`, logs `jn`.
- Badges: `PK` (amber), `FK` (violet, real Django FK), `SOFT` (blue, string ref — no DB constraint), `UQ` (green). SOFT marks cross-app seams — never mislabel an FK as SOFT or vice versa.
- Fields: 3–9 per node, the columns that matter. Types are short lowercase hints (`uuid`, `paise`, `enum`, `json`, `bool`, `self`, `deprecated`).
- **Positioning math**: node height `h = 30 + rows*19 + 8`. Lay nodes in columns at x ≈ 30 / 330 / 645 / 920 / 1180 (domain A left, junctions center, domain B right). Vertical rule: `y_next ≥ y + h + 20`. Long column names need wider `w` (chars × 6.4 + 90).
- Canvas: default `1420 × 880`. If nodes exceed it, update THREE places: svg `viewBox`, dotgrid `<rect>` size, and `applyZoom()` constants.
- Edges: `[from, to, 'fk'|'soft']` — direction = data flow. Edges routing under cards is fine (nodes paint on top).

## @DATA:FIELD_ENUMS — chip popovers

```js
'nodeId.field_name': {name:'ExactEnumClassName', vals:[['VALUE','4-5 word description'], …]}
```
- Key MUST equal the displayed field name (that's how the hover hit-zone binds).
- Values MUST be read from `constants/enum.py` — never from memory or docs.
- Descriptions: 4–5 words, state what the value MEANS in the lifecycle ("pay clicked; 5-min hold"), not a restatement of the name.

## @DATA:FIELD_INFO — prose popovers

```js
'nodeId.field': {name:'Table.field — hook phrase', dep?:true, rows:[['<b>lead.</b> sentence.'], …], warn?:'red strip text'}
```
Write one for every column a newcomer could misuse:
- **Sibling amounts/dates/statuses** → each popover contrasts against the siblings ("Razorpay reads THIS field, always").
- **Deprecated** → `dep:true` (renders red DEPRECATED chip) + why it still holds data + `warn:'Do not build new logic on this field.'`
- **Same word, different meaning across apps** (the fee TDR vs payments TDR case) → both sides get a `warn` naming the other.
- 2–3 rows max, ≤20 words each, `<b>` the load-bearing phrase.

## @DATA:CHIP — status colors

Semantics, not aesthetics: `ok`=terminal success · `warn`=waiting on someone · `info`=in flight/created downstream artifact · `bad`=failed/cancelled/removed/deprecated · `neutral`=initial/draft · `viol`=meta/audit actions. Every status string that appears in SCENES or popovers needs an entry (missing → grey fallback).

## @DATA:TABLES — story deck

```js
key: {title:'DisplayName (unit)', app:'fe|pe|jn', cols:['id','status',…]}
```
Only tables the story writes to. ≤6 columns each — the columns the beats touch. Put the unit in the title when amounts appear (`(paise)`, `(₹)`).

## @DATA:FLOW — flow-chart nodes

One node per scene: `{icon, lbl, actor?}`.
- `actor` ONLY for non-system steps: the human or external party (`OFFICER`, `CITIZEN`, `RAZORPAY`, `INSPECTOR`, `BANK`…). System steps get no badge.
- Icon from `LICON` (see library below). Add new lucide paths to `LICON` if needed — stroke-style 24×24 lucide paths only, never filled/Material icons.

**Icon library shipped in LICON**: `calc` (calculator), `db` (database), `officer` (user), `receipt`, `citizen` (user-round), `zap` (webhook/event), `check` (terminal success). Common additions, paste-ready lucide paths:
- `doc` file-text: `<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M16 13H8"/><path d="M16 17H8"/><path d="M10 9H8"/>`
- `bank` landmark: `<line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/>`
- `clock` timer: `<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>`
- `mail` notification: `<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>`
- `x` cancel: `<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 15 6-6"/>`
- `workflow` automation: `<rect width="8" height="8" x="3" y="3" rx="2"/><path d="M7 11v4a2 2 0 0 0 2 2h4"/><rect width="8" height="8" x="13" y="13" rx="2"/>`

## @DATA:SCENES — the story

Shape: `{title, tables:[deck keys], beats:[…]}` × 5–8 scenes, 4–10 beats each.

Beat vocabulary (the engine handles all animation):
| Beat | Effect |
|---|---|
| `{say, sub, d}` | Narration headline + muted subline. `say` may embed `<span class="tok">…</span>` glow tokens (ids, amounts, event names — 1 per scene max). `sub` may use `<code>`, `<b>`, `<span class="hl">` |
| `{add:'table', id, cells:{…}, d}` | Row slides in; deck auto-switches to that table |
| `{set:'table', id, cells:{…}, d}` | Cells flash amber; status strings auto-render as chips |
| `{set…, kill:true}` | Soft delete — row struck through red (use for is_deleted flips) |
| `{note:'html', d}` | Violet gotcha callout (invariants, locks, traps). Max ~1 per scene; `<b>` lead phrase |
| `d` | ms until next beat: 1200–1600 row writes, 2200–3000 narration/notes |

Rules:
- Scene 1 = trigger + config resolution. Middle = writes + human actions. Final scene = terminal cascade + an epilogue `say` pointing to the downstream flow.
- Narration: present tense, one actor per sentence, concrete values ("Priya overrides Labour Cess to ₹10,000").
- Every mutation the narration claims must appear as an `add`/`set` beat — no invisible writes.
- IDs stay consistent across scenes (`set` needs the `add`'s id).
- End state must include one unfinished thread (an unpaid order, a pending step) — real systems don't end neatly.

## QA checklist (run all)

1. `node --check` on the extracted script.
2. Grep for source-example leftovers: `fee_engine|payments_engine|Ravi|Priya|efr_|ord_7c|APP-BP` → 0 hits (unless module IS fees).
3. Popover keys ⊆ displayed field names; SCENES statuses ⊆ CHIP; beat tables ⊆ TABLES; |FLOW| == |SCENES|.
4. Node overlap math per column; canvas constants updated together (3 places).
5. Browser pass: schema hover-isolation, enum + info popovers, fullscreen, zoom, play end-to-end, prev/next beat stepping, pill deck follows writes, light theme readable.
