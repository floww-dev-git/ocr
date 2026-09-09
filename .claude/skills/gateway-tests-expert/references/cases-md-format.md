# `cases.md` — the per-operation format

`cases.md` is the per-operation source of truth for a gateway-test package: **one table, one row
per case**, saying what the case drives and what it proves. It must read like a record of what
the test actually proved — not a rule book of intentions, and not a second copy of the world.
The world lives in `factory_jsons/`; the row names that file and nothing more.

> **Current ruling (2026-07-30, user): `cases.md` is TABLE-ONLY.** The per-case `###` sections are
> gone, and with them the `Arrange — load-bearing` table, the `Act` block and the numbered `Assert`
> list. The reason is measured: 5,235 of the 5,237 arrange rows had their key or their value
> already sitting in the fixture JSON — the table was a second source of truth for the world, and
> that numbered list was the test's own `assert` statements written twice. `Assertions` — the
> plain-English claims — is now the ONLY record of what a case proves, and it is required, not
> optional. **A file that still
> carries `###` per-case sections has not been converted.** Convert it; never copy its shape into
> a new file.

The TESTS still use Arrange / Act / Assert — that is pytest structure and it did not change. Only
the way `cases.md` DOCUMENTS a case changed.

## Document structure (top to bottom)

1. **Title** — `# <operationName> — test cases` (the gateway operation's real name).
2. **Intro** — 2-4 lines: what the operation does and the behaviours the cases hang on
   (precedence, derived kinds, guards, ordering). Ends with `**N cases, G groups, all covered.**`
3. **Findings** (optional) — a short list of what the code read surfaced (dead branches, traps).
   This is the only prose section that may run long, and only when there is something real to say.
4. **The Groups legend** — one `**Groups:**` line naming every group. Required; see Grouping below.
5. **The `<style>` block** — verbatim, below. It styles the table.
6. **The case table** — one row per case. This is the rest of the document.

### The count line

The intro's last line says how many cases this file holds and how many groups they fall into.
**N must equal the number of rows in the table, G the number of groups** — count them, never
carry a number over from the plan. A stale N is a bug (one file claimed 59 over a 62-row table;
another claimed 14 over 15). Three forms:

- **Canonical** — `**N cases, G groups, all covered.**` Use it whenever every case is covered.
- **Partial coverage** — `**N cases, G groups, M covered.**` REQUIRED, not optional, when
  coverage is incomplete, and it must name what is uncovered and why. Never write "all covered"
  when it is not true; the file would be lying — and the checker stops enforcing `Test` links the
  moment you stop claiming coverage, so the honest form costs nothing. Real examples:
  `**32 cases, 10 groups, 26 covered.** Cases J2 and J3's generation half are NOT covered: both are draft-generation properties, unreachable from this door, and blocked on a reconciliation-config builder graph that does not exist (index open-debt #7). The machine's half of case J3 — the split rows summing back exactly — IS covered.` ·
  `**15 cases, 7 groups, none covered.** The cases below are planned from the code read; no test file is written yet.`
- **Trailing parenthetical** (optional) — reconciles the count against what the index planned, or
  against the test-file count when a case owns more than one test method:
  `**8 cases, 3 groups, all covered.** (The index estimated ~7; the extra is the no-holds-exist proof.)` ·
  `**11 cases, 4 groups, all covered.** (13 tests — cases B2 and C1 each carry a second method for their sibling-shape checkpoint.)`

## Grouping — every file, no exceptions

Case ids are **letter-grouped**: `A1`, `A2`, `B1`, … The letter names a theme; the number is the
case's position inside it. A suite of any size gets them — a 4-case file has 2 groups, a 62-case
file has 18.

WHY: a bare number carries nothing. `case 34` tells a reader neither what it covers nor where it
sits, so a 23-row table has to be read end to end to find the selection guards. `C3` says which
concern it belongs to before you read the row, and the legend gives the whole shape of the suite
in one line. It also makes a gap visible: a suite whose errors group holds one case is a question.

Five rules:

1. **Letters are positional — `A`, `B`, `C` … in table order.** Never mnemonic. `RM1` for remove,
   `H1` for happy, `E4` for error read as a private code, and they collide across suites (`E` was
   *errors* in one file and a group *name* in another). The legend carries the meaning; the letter
   only carries the order.
2. **A group is ONE contiguous run of rows.** Grouping does not reorder anything — rows stay in
   increasing order of complexity (below), and the groups are the runs that order already forms.
   If a theme is not contiguous, either the row order is wrong or it is two themes.
3. **Errors and access guards come last** — the final group(s), matching the complexity order.
4. **Group names are plain-English themes, 1-4 words**, from the operation's own vocabulary:
   `Selection guards`, `Installments`, `Refund events`, `Missing access check`. Not layer nouns,
   not `Misc`.
5. **Aim for 2-5 cases per group.** One case alone is fine when the concern is genuinely singular
   (a shipped bug, a door gap); a group of nine means there is a split hiding inside it.

### The legend

One line in the intro, below the count line and any findings:

```markdown
**Groups:** A · Add & calculate — B · Installment parent→children — C · Direct-order adjustment — D · Grouping — E · Guards & no-ops — F · Errors
```

Letters in table order, ` · ` between a letter and its name, ` — ` between groups. It may wrap.
The legend and the table must agree — the checker compares them.

### Citing a case

Prose cites a case by its **grouped id**, never a bare number: "the same world as case A1",
"exactly like case C1 proves for the admin guard". A bare `case 7` is banned outright: when a
case is inserted or a group is resplit, every bare number silently re-points at the wrong row,
and nothing anywhere breaks (`plain-language.md`, "Stable citations — never cite by position").
The checker fails on any `case <number>` left in a file.

## The `<style>` block

Embed verbatim (neutral greys deliberately — blue-tinted greys were explicitly rejected):

```
<style>
/* Full borders + zebra striping for the pipe tables below.
   Honoured by the VS Code / browser preview; GitHub strips this block
   but applies its own bordered + striped table styling anyway. */
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #cfcfcf; padding: 8px 12px; text-align: left; vertical-align: top; }
thead th { background: #dcdcdc; font-weight: 700; }
tbody tr:nth-child(odd)  { background: #ffffff; }
tbody tr:nth-child(even) { background: #ededed; }
@media (prefers-color-scheme: dark) {
  th, td { border-color: #3b3b3b; }
  thead th { background: #262626; }
  tbody tr:nth-child(odd)  { background: #151515; }
  tbody tr:nth-child(even) { background: #212121; }
}
</style>
```

## The case table

Header and alignment rows, EXACTLY these — six columns, in this order, in every file:

```
| Case | Title | What it drives | builder_json | Assertions | Test |
|---|---|---|---|---|---|
```

| Column | Rule |
|---|---|
| Case | The letter-grouped id — `A1`, `A2`, `B1`, … See Grouping above. Never a bare number |
| Title | Short behaviour name, plain English — what the case proves, not how |
| What it drives | The 1-2 sentence lead: the world and the act, in words. An *italic* aside (`*Finding.*`, `*Capstone.*`, `*External.*`) OPENS the cell when the case carries one — the report derives its badges from these |
| builder_json | The fixture FILENAME only, backticked: `` `update_plain_field_smoke.json` ``. Not a path — the folder is always the suite's `factory_jsons/`, so it is implied. `<br>`-separate when the case loads more than one |
| Assertions | What the case proves, `<br>`-separated, one claim per entry. Plain English, intent first. Required |
| Test | Relative hyperlink: `[test_x.py](test_x.py)` |

### The Assertions column

An assertion here is a plain-English CLAIM, never a copy of the test's `assert` statements — the
code stays in the test. This is the whole record of the case now, so the column carries three
things the sections used to split:

- **The claims.** One per `<br>`, each a sentence a reader can check against the test.
- **A multi-run case's runs.** A case whose test file holds several test methods (three licence
  states; an on / off / not-applicable triple) is still ONE row. Each run becomes its own
  assertion, bold-labelled when the runs need naming — `**Turns on.** …<br>**Turns off.** …` —
  rather than a `**Run N —**` heading.
- **The notes.** An observation the claims cannot state — a `*Finding.*`, a measured cost, a
  "this branch has no producer", a regression net — rides as a trailing *italic beat.*

### Worked example

The real first row of
`sales_crm_core/tests/gateway_tests/update_application_field_in_portal/cases.md`:

```markdown
| Case | Title | What it drives | builder_json | Assertions | Test |
|---|---|---|---|---|---|
| A1 | Update a plain field | A citizen owns an application on a customer portal. The mutation sets one plain text field to a new value. | `update_plain_field_smoke.json` | Response is the plain field-response branch carrying the field id and the new value<br>the record field response in DynamoDB now holds the new value<br>the application's Elasticsearch document reflects the new value<br>no error branch is returned | [test_update_plain_field_smoke.py](test_update_plain_field_smoke.py) |
```

## Where the arrange data lives

`factory_jsons/<case>.json` is the **single source of truth for the world** — every entity the
case needs, cross-app included. `cases.md` restates none of it. A mirrored world is a second
source of truth that goes stale on the next fixture edit, and it is what the table-only ruling
removed.

The report closes the gap without hand-copying. Start it with:

```bash
python3 html_report_templates/gateway_test_cases_report/serve.py
```

It serves the repo, lists every suite, and reads each `cases.md` and its `factory_jsons/*.json`
live off disk — so the full world is rendered beside the case it belongs to, always current.

## Language rules

- **Plain English, intent first**, in the Title, `What it drives`, and every assertion. A reader
  who does not know the schema still has to get the point.
- **Code font only where the exact name IS the claim** — a config constant the case turns on
  (`` `B_PASS_JSON_CONFIG` ``), a method a spy proves is never called
  (`` `resolve_ltp_autofill_responses` ``), a response field the case is about
  (`` `changedRequiredFieldStates` ``). Do not code-font a field name that plain words carry.
- **No invented names.** Every identifier must exist in the fixture, the test, or the schema. If
  you are about to write a name you have not read, stop and read it.
- Domain terms come from the code's own vocabulary (`clean-code.md`) — never a synonym.
- Bold is reserved for the `**N cases, G groups, all covered.**` count, the `**Groups:**` legend,
  and a multi-run assertion's run label.
- Keep cells readable: no line breaks inside a cell — separate entries with `<br>`.

## Row ordering

Cases in **increasing order of complexity**: simplest smoke first, comprehensive/critical last,
error and edge cases slotted where their complexity fits. This is the recommended authoring and
fan-out order too. The groups are the runs this order already forms — grouping never reorders
rows, it names the runs (see Grouping).

## The contract with the tests

Every assertion MUST be something the test actually proves — through its response snapshot, its
stores snapshot, or an explicit `assert` statement. After the tests are green, cross-check each
assertion against the GENERATED snapshot (read the snapshot file); only then is the row, and the file's
`**N cases, G groups, all covered.**` claim, true. If the test and the row disagree, one of them is
wrong — fix it; never leave drift. The `builder_json` cell must name a file that exists in the
suite's `factory_jsons/`, and the `Test` link a file that exists in the suite.

Run the checker — it is the mechanical half of everything above:

```bash
python3 .claude/scripts/check-cases-md.py                  # whole repo
python3 .claude/scripts/check-cases-md.py <app-or-suite>   # one app or suite
```

It fails on ungrouped ids, a split group, a legend that disagrees with the table, a wrong count
line, a case cited by bare number, and a missing fixture. `Test` links are enforced only once the
count line claims `all covered` — before that a dangling link is a note, because the file is
written before the tests exist.

## Two authoring directions

| Situation | Direction |
|---|---|
| **New suite** (the normal case) | `cases.md` is written FIRST, from the code read. `What it drives` is the world you are about to build and the call you are about to make; the assertions become the test's `assert` statements; `builder_json` names the fixture you are about to write |
| **Retrofit** of a suite whose tests are already green | Derive from the tests — they are the ground truth for what executes. Read each test's `given(...)` fixture for the `builder_json` name and its `assert` lines for the assertions. Never re-derive from memory or from an older prose row |
