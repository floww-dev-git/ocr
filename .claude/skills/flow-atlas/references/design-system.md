# Flow Atlas — Product Design Specification

A design system for **interactive system-documentation screens**: pages that teach how a backend flow works by showing its data entities, their relationships, and an animated step-by-step story of one lifecycle. Applicable to any implementation flow (payments, approvals, refunds, reconciliation, onboarding, document workflows).

Give this document to a screen generator (Stitch) together with the flow-specific content; every visual decision needed is specified here.

---

## 1. Product Concept

| Aspect | Definition |
|---|---|
| Product type | Read-only interactive documentation / explainer surface |
| Audience | Engineers, reviewers, business/ops teams learning a system flow |
| Page job | Build a mental model: WHAT exists → HOW it connects → WHAT happens over time |
| Tone | Cinematic but precise. Confident, technical, zero marketing fluff |
| Structure | Every page = 3 acts, in this order: **I. Inventory** (entity cards) → **II. Relationship map** (graph) → **III. Animated story player** (scene-by-scene lifecycle) |

---

## 2. Theme — "Midnight Forge" (dark, default) + "Daylight Parchment" (light)

Dark-first. Light theme is a full companion, not an inversion. All colors are tokens; components never hardcode hex.

### 2.1 Color tokens

| Token | Dark | Light | Use |
|---|---|---|---|
| `bg` | `#0a0912` | `#faf7f1` | Page ground (indigo-tinted black / warm parchment) |
| `surface` | `#15131f` | `#ffffff` | Cards, panels |
| `elevated` | `#201d2e` | `#ffffff` | Nested cards, table headers, rails |
| `border` | `#322e46` | `#ebe4d8` | All strokes, 1px |
| `text` | `#f4f2fc` | `#181620` | Primary text |
| `muted` | `#a3a0b8` | `#6a6776` | Secondary text, captions |
| `primary` | `#ff9a3c` | `#f1701a` | Brand amber — domain A, CTAs, active states, progress |
| `accent` | `#b18bff` | `#7c3aed` | Violet — junction/audit/meta entities, secondary emphasis |
| `info` | `#4fb7ff` | `#0a86da` | Sky blue — domain B, in-progress states |
| `success` | `#2fe3a3` | `#06a06d` | Completed / positive states |
| `warning` | `#ffc63d` | `#d97706` | Pending / attention states |
| `danger` | `#ff6b6b` | `#e83a3a` | Removed / failed / cancelled states |
| `grey` | `#8e8ca8` | `#6a6776` | Neutral / initial states |

### 2.2 Semantic color rules

- **Domain hue coding**: each subsystem in the flow gets ONE hue — domain A = `primary` (amber), domain B = `info` (blue), cross-cutting/junction/audit = `accent` (violet). Applied consistently to card rails, graph nodes, table header dots.
- **State colors are reserved for state** (chips, status text) and never used as decorative accents.
- One bold element per component; everything around it stays quiet.

### 2.3 Atmosphere

- Page background carries three faint radial glows pinned to corners (amber top-left, violet top-right, blue bottom-right), ~10% opacity, fixed attachment.
- Elevation: `0 10px 34px -12px rgba(0,0,0,.7)` (dark) / `0 10px 30px -16px rgba(20,20,30,.28)` (light).
- Emphasis glow (active/highlighted cards): 1px ring + 22px soft outer glow in the element's hue at ~40–50% opacity.

---

## 3. Typography

| Role | Face | Treatment |
|---|---|---|
| Display / headings | Geist → Inter → system-ui | Weight 700–800, letter-spacing −0.02em, `text-wrap: balance` |
| Body | Same sans | 15–17px, line-height 1.55–1.65, max ~65ch |
| Data / code / labels | Geist Mono → JetBrains Mono → ui-monospace | Ligatures OFF, tabular numerals for all figures |

Scale:

| Level | Size | Notes |
|---|---|---|
| Hero H1 | clamp(34–58px) | Two-tone: each domain name in its hue |
| Section H2 | clamp(24–34px) | Preceded by act eyebrow |
| Card title | 15px mono bold | Entity names always mono |
| Body / role text | 13–15px | Muted color for descriptions |
| Data cells | 11.5–12.5px mono | Tabular nums |
| Eyebrow / labels | 10–13px mono | UPPERCASE, letter-spacing 0.15–0.22em, primary color, short leading dash/rule |

---

## 4. Layout

- Content column: max 1240px, 28px side gutters, centered.
- Section rhythm: ~54px vertical padding; hero ~84px top.
- Eyebrow pattern above every section: `ACT I` / `ACT II` / `ACT III` (numbering encodes the real reading sequence) + H2 + one muted subtitle paragraph (≤72ch) that states the section's key insight.
- Card grids: `auto-fill, minmax(360px, 1fr)`, 18px gap.
- Corner radius: 14px cards, 10–12px nested elements, 999px pills.
- Wide content (tables, graphs) scrolls inside its own container; the page never scrolls horizontally.

---

## 5. Components

### 5.1 Hero

- Eyebrow → two-tone H1 (domain names colored by their hue) → 1–2 sentence lede (muted) → row of pill badges.
- Badges: mono 12px, pill, surface background; each carries a colored square dot for its domain + one hard fact (e.g. unit conventions, boundary rules). No imagery.

### 5.2 Entity card (Act I)

The atom of the inventory act. One card per entity/table/concept.

- Surface card, 3px colored left rail in the entity's domain hue.
- Header row: entity name (mono, bold) + role tag pill (tiny mono uppercase, outlined in domain hue) right-aligned.
- One-line role description (muted, may contain emphasis).
- Attribute list: rows separated by dashed hairlines; each row = attribute name (mono) + optional badge + right-aligned muted annotation.
- Attribute badges (tiny outlined squares, mono 10px): `PK` (warning hue), `FK` (accent), `SOFT` (info — reference without enforcement), `CRIT` (danger — business-critical field). Badge vocabulary is adaptable per flow but stays ≤4 kinds.
- Hover: lift −3px, border warms toward domain hue.
- After the grid: a "supporting cast" strip — small mono chips naming secondary entities with a one-clause description each.

### 5.3 Status chip

Pill, 10px bold mono uppercase, tinted background (12% hue) + 55% hue border + hue text. Variants: `ok` (success), `warn` (warning), `info` (blue), `bad` (danger), `neutral` (grey), `meta` (violet). Every state value in the product renders as a chip — never plain text.

### 5.4 Relationship map (Act II)

- Full-width panel containing a node-edge graph; horizontally scrollable on small screens.
- Node: rounded rect, elevated fill, domain-hue border + 3.5px left rail, title (mono bold 12px) + subtitle (muted 9.5px).
- Edge grammar (this is information, not decoration):
  - **Solid line** = enforced/hard relationship.
  - **Dashed line** = soft reference (no enforcement) — visually flags risk seams.
  - Animated flow particles (3px dashes drifting along the path, staggered delays) show data-flow direction.
- Hover/focus a node → isolate: neighbors stay, everything else dims to ~15% opacity; the node gains its hue glow.
- Legend row below: line samples + domain color dots, mono 12.5px.

### 5.5 Story player (Act III) — the signature component

A media-player metaphor for data mutation over time.

Layout (desktop): left rail 280px + main stage; footer control bar spans both.

- **Scene rail**: numbered scene list (`01`–`NN` mono numerals in primary; titles in sans 13.5px). Active scene = 3px left bar in primary + faint primary wash. Completed scenes' numbers turn success green. Click = jump. On mobile the rail becomes a horizontal scrollable tab row.
- **Narration zone** (top of stage): one bold headline sentence (17.5px, balanced) + one muted sub-sentence with inline highlights (primary color) and inline code tokens. Reads like a narrator, present tense: "The officer overrides the amount…".
- **Note callouts**: violet-tinted rounded cards for gotchas/invariants ("**Order matters silently.** …"). Max 2 visible; older ones roll away.
- **Mini data tables**: grid of live tables (auto-fit minmax 330px). Each = elevated card, header with domain dot + entity title (mono), column headers uppercase 10px muted, data rows mono 11.5px tabular. Empty state shows "— empty —" inline in the header. The currently-acting table gets the hue glow ring.
- **Row/cell motion** (the "video" effect):
  - New row: slide in from left 14px + fade, 0.55s, slight overshoot easing `cubic-bezier(.2,.9,.3,1.2)`.
  - Changed cell: amber background flash decaying over 1.15s.
  - Removed row: keep it — strike-through in danger color at 60% opacity (soft-delete visual).
  - Status changes morph chip color.
- **Control bar**: Play/Pause (solid primary button, dark-on-amber text) · Restart (ghost button) · progress bar (5px pill, primary→accent gradient fill) · scene counter (mono, muted).
- **Behavior**: autoplays when scrolled into view (once); Space toggles, ←/→ jump scenes; jumping replays prior state instantly then animates forward. Beats run ~1.2–3s each, longer for narration-heavy beats.

### 5.6 Footer

Hairline rule + one mono muted line: data provenance ("verified against …") and abbreviation glossary.

---

## 6. Motion Language

| Motion | Spec |
|---|---|
| Row entry | 0.55s, slide-x −14px + fade, overshoot ease |
| Cell change | 1.15s background flash (primary → transparent) |
| Card hover | translateY(−3px), 0.25s ease |
| Focus/active glow | 0.4s ease border + shadow transition |
| Edge flow particles | linear infinite, 1.6s cycle, staggered 0.13s per edge |
| Scene narration swap | 0.3s opacity |
| Progress bar | width transition 0.35s linear |

Rules: motion always **means** something (a write, a state change, a direction). No decorative parallax. `prefers-reduced-motion` collapses everything to instant final states; the player still works as a stepper.

---

## 7. Voice & Copy

- Narration: present tense, one actor per sentence, concrete values ("Ravi pays ₹54,000 via UPI").
- Notes state invariants and traps, bolded lead phrase, ≤2 sentences.
- Subtitles under section headings deliver the ONE insight of the section, not a summary.
- Real example data everywhere — realistic IDs, amounts, timestamps. Never lorem, never `foo`.
- Inline `code` styling for identifiers, field names, formulas.

---

## 8. Recipe — applying this to a new flow

1. **Pick domains**: identify 2 subsystems + the cross-cutting layer → assign amber / blue / violet.
2. **Act I**: list 8–15 core entities; for each: name, role tag, one-line role, 5–9 critical attributes with badges; push the rest into the supporting strip.
3. **Act II**: draw nodes clustered by domain (domain A left, domain B right, junctions center); classify every relation solid vs dashed.
4. **Act III**: write ONE concrete story instance with real numbers. Break into 5–8 scenes, each 4–10 beats; every beat is a row insert, cell change, status morph, narration, or note. End with an epilogue pointing to the downstream flow.
5. **States**: enumerate every status value and map each to a chip variant before building.

---

## 9. Screen inventory (for generation)

| # | Screen | Content state |
|---|---|---|
| 1 | Full page — hero + Act I atlas | Cards populated, one card hovered |
| 2 | Act II relationship map | Default state, all edges flowing |
| 3 | Act II relationship map | One node hovered — neighborhood isolated, rest dimmed |
| 4 | Act III player — idle | Scene 1 selected, tables empty, "Ready when you are" |
| 5 | Act III player — mid-story | Scene 3–4 active, tables part-filled, a cell mid-flash, one note visible |
| 6 | Act III player — complete | Final scene, success chips everywhere, replay button |
| 7 | Mobile (≤900px) | Rail as horizontal tabs, single-column tables, cards stacked |
| 8 | Light theme variant of screens 1 & 5 | Daylight Parchment tokens |
