# Plain Language — shared writing standard

Load-on-demand reference. Applies to every user-facing artifact AND chat: user stories, PRDs,
ADRs, dashboards, task breakdowns, review reports, status updates, and replies. Assume the reader
is a **non-native English speaker** and an **SDE-1** — write so both understand on the first read.

## Rules
- **Short sentences. One idea per line.** If a sentence needs a fancy word to sound right, rewrite the sentence.
- **Describe things by what they DO**, not by implementation jargon.
- **A small diagram beats prose** when the thing has shape (a flow, a before/after) — show, then tell.
- **No unexplained fancy terms.** If a phrase needs explaining, it is the wrong phrase — say it plainly.

## Banned words — say them plainly instead

| Don't write | Write |
|---|---|
| second pass | a second read / the second time it runs |
| reconstitution | build the objects (from the stored rows) |
| anti-corruption point / layer | the boundary where we translate |
| OCP invoice | (drop it — just say what the change costs) |
| orchestration layer | the part that runs the steps in order |
| load-bearing | it matters because … / it holds up … |
| steel thread | the first thin end-to-end path |
| strategy pattern | plug in a new X |
| byte-match | same behaviour as today |

## Nicknames — name the thing instead

A **nickname** is a metaphor coined inside one feature for a thing that already has a real name. It is the worst class of jargon: unlike a fancy word, there is nowhere to look it up. The reader either was in the room when it was coined, or is locked out.

The test is not "is it a term?" — it's **"can the reader look it up?"** `slice`, `integration closer`, `consumer-first`, `build-once` are project vocabulary with a defined home (`dev-loop.md`, `engineering-canon.md`) — those are fine. The rows below have no home anywhere.

| Don't write | Write |
|---|---|
| the door | the interactor / name it: `ExecuteTransitionInteractor` |
| a press | a transition attempt / when someone tries to move an item |
| the walk | the guard evaluator / the thing that runs the guards in order |
| umbrella row | the slice's parent row |
| the battery | the set of guards |
| the diary | (name the actual record — an audit log? a state record?) |

**Clarity is not reader-dependent.** A nickname costs a developer agent the same inference, and the same chance of resolving it wrong, as it costs a person. Never justify one with "the agent knows what it means."

*(Census that produced these rows, 2026-07-16, across REF-001's 8 tasks files: "the door" ×54 · "a press" ×20 · "the walk" ×17 · "umbrella row" ×18. Two already-banned words — "steel thread" ×3, "load-bearing" ×1 — also shipped, from this config's own skills. A banned-word table that nothing checks is a wish.)*

This list grows: when the user or a reviewer flags a fancy word, add the row (route to dhruva).

## Stable citations — never cite by position

A nickname fails because the reader cannot look it up. A **positional citation** fails worse: the reader looks it up and gets the *wrong thing*, with no signal that anything moved. Both are referential-clarity bugs; this one is silent.

A positional citation points into a list by its ordinal — `ADR-002 D8`, `US-11 AC5`, "the third bullet". Those ordinals are not identity. They shift whenever anything is inserted or renumbered, and nothing anywhere breaks.

| Don't write | Write |
|---|---|
| `ADR-002 D8` | the cutover-strategy fork — `adrs/ADR-002-*.md`, "Decision: cutover strategy" |
| `US-11 AC5` | US-11, "system actor may enrol without a role" |
| "see the third bullet" | quote the 3-5 words you mean |

### Rules
1. **Cite by NAME + PATH, not by number.** A name survives renumbering; if the name changes, the citation fails loudly and greppable — which is the point.
2. **A bare number may ride ALONGSIDE a name** as a convenience (`ADR-002 "cutover strategy" (D8)`), never instead of it.
3. **Acceptance criteria are APPEND-ONLY once anything cites them.** Adding an AC mid-list silently re-points every citation past the insertion. Append it last, or give ACs stable ids in the story file so position stops mattering.

### WHY (REF-001, 2026-07-20)
Three `ADR-00N Dn` pointers rotted through decision renumbering on one feature. One turned *dangerous*: a doc cited "the standing ADR-002 D8 fork" when ADR-002 had no D8 — then an architect legitimately added a real D8 for an unrelated decision, so the stale pointer now resolves to something plausible and wrong. Separately, an AC inserted as US-11's 5th bullet shifted the meaning of every "AC5"/"AC6" citation in a whole tasks file; it was fixed by appending it last instead.

A checker cannot save you here — the dangerous case is the one that *resolves*. Only the citation form prevents it.
