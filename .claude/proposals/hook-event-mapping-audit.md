# Hook Event Mapping Audit

**Date:** 2026-07-29 · **Claude Code:** 2.1.220 (`claude --version`) · **Scope:** `.claude/settings.json` hooks

---

## TL;DR

The five blocking validators are on the wrong event — but **moving the event alone would silently break all
five**, because every one of them reads the file from **disk**, not from the hook payload. On PostToolUse the
disk holds the new content. On PreToolUse it holds the *old* content. A naive event swap turns five working
validators into five that validate the previous version of the file and report clean.

So this is not a settings-only change for four of the five. The one exception — `check-review-file.py`'s
filename rule — needs nothing but `tool_input.file_path` and can move today with a flag.

Second finding: all nine PostToolUse hooks are wired to **every** Edit|Write, and each of the five blocking
ones does its own path filter in Python. The filtering itself is cheap (measured 21–31 ms per no-op
invocation, and the docs say matching hooks run in parallel — so the wall-clock cost is ~31 ms, not the
121 ms sum). The reason to narrow with `if` is **failure surface**, not latency: five interpreters that must
start, import, and early-exit correctly on every single edit is five chances for an unrelated edit to be
blocked by a hook that has no business looking at it.

---

## Verified hook semantics

All quotes from <https://code.claude.com/docs/en/hooks> (fetched 2026-07-29; `docs.claude.com/en/docs/claude-code/hooks`
301-redirects there).

**PreToolUse receives full tool input for Edit and Write.** Verbatim from the PreToolUse event reference:

```json
"tool_name": "Edit",
"tool_input": {
  "file_path": "src/app.ts",
  "old_string": "function oldName() {",
  "new_string": "function newName() {"
}
```
> For Write tool, `tool_input` contains:
> ```json
> { "file_path": "src/config.json", "content": "{ \"key\": \"value\" }" }
> ```

**Exit code 2 means different things per event.** Verbatim:

| Event | Blocks? | Behaviour |
|---|---|---|
| `PreToolUse` | Yes | "Blocks the tool call" |
| `PostToolUse` | No | "Shows stderr to Claude; the tool already ran" |

> "**Exit 2** means a blocking error. Claude Code ignores stdout and any JSON in it. Instead, stderr text is
> fed back to Claude as an error message."

PreToolUse also supports a richer JSON form (`hookSpecificOutput.permissionDecision: "deny"` +
`permissionDecisionReason`), which produces a cleaner denial than a raw exit 2.

**`async`** — verbatim: "If `true`, runs in the background without blocking." There is also `asyncRewake`:
"runs in the background and wakes Claude on exit code 2." An `async` hook therefore **cannot block**, which is
why the five validators are correctly synchronous today.

**`if`** — verbatim: "Permission rule syntax to filter when this hook runs, such as `"Bash(git *)"` or
`"Edit(*.ts)"`. The hook command only runs if the tool call matches the pattern. Only evaluated on tool
events: `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PermissionRequest`, and `PermissionDenied`."

**Matchers filter tool NAME, never file path.** Verbatim: "For tool events … matchers filter by **tool name**,
not file path… File path filtering is done via the `if` field on individual handlers, not the matcher."

**File patterns use gitignore syntax** (<https://code.claude.com/docs/en/permissions>): "Read and Edit rules
both use [gitignore] pattern syntax… Bare filenames follow gitignore semantics and match at any depth, so
`Read(.env)` and `Read(**/.env)` are equivalent." And, for v2.1.210+: "Use `Edit(docs/**)` in place of
`Write(docs/**)`… **(Edit rules cover all file-editing tools)**" — so a single `if: "Edit(...)"` should cover
Write too (see *Unverified* below).

**Hook dedup** — verbatim: "All matching hooks run in parallel, and identical handlers are deduplicated
automatically. Command hooks are deduplicated by command string and `args`." Whether `if` participates in the
dedup key is **not documented** — this matters, see Recommendation 3.

---

## The central finding: all five read from disk

Evidence — none of the five reference `new_string` or `content`; all five call `open(path)` on
`tool_input.file_path`:

| Script | Content source | Line |
|---|---|---|
| `check-task-ordering.py` | `open(path)` | `.claude/hooks/check-task-ordering.py:245` |
| `check-tick-evidence.py` | `open(path)` | `.claude/hooks/check-tick-evidence.py:145` |
| `check-dead-contracts.py` | `open(path)` | `.claude/hooks/check-dead-contracts.py:118` |
| `check-tasks-yaml.py` | `load(path)` → `open(path).read()` | `.claude/hooks/check-tasks-yaml.py:85`, `.claude/scripts/tasks_lib.py:59` |
| `check-review-file.py` | `open(path)` | `.claude/hooks/check-review-file.py:160` |

Demonstrated live — a payload whose `tool_input.content` is a perfectly clean review, pointed at a junk file
on disk, produces four findings from the **disk** content and exit 2:

```
$ python3 .claude/hooks/check-review-file.py < payload.json   # tool_input.file_path=/tmp/…/badname-review.md
Review file validation failed for /tmp/hooktest/reviews/badname-review.md:
  - no `## Escaped Cases` section …
  - no `## Plan Defects` section …
  - no Learnings …
  - no routable verdict …
EXIT=2
$ cat /tmp/hooktest/reviews/badname-review.md
# junk
no sections here
```

**Consequence:** on PreToolUse these scripts would read the pre-write file. Two failure modes, both silent:
a bad write passes because the old content was fine, and a *repair* write is blocked because the old content
was bad. The second is worse — it makes the file unfixable.

**To move any of them, the script needs a content-reconstruction step:**
- **Write** → `tool_input.content` is the complete new content. Trivial, exact.
- **Edit** → read disk + apply `old_string` → `new_string` (honouring `replace_all`). The hook now
  re-implements Edit's replacement semantics; a divergence here produces wrong verdicts.

There is already a working precedent for validate-then-write in this repo: `.claude/scripts/tasks.py:97-101`
runs `validate_all(updated, …)` and returns 1 **before** calling `dump(updated, path)`. That is exactly the
shape a PreToolUse hook needs.

---

## Per-hook table

| Hook | Current event | What it validates | Input it needs | Correct event | Why | Risk of moving |
|---|---|---|---|---|---|---|
| `check-review-file.py` **(filename rule)** | PostToolUse (blocking) | Filename matches `s<N>-<scope>-review.md` / `final-review.md` inside a feature folder (`:42`, `:106`) | **`tool_input.file_path` only** | **PreToolUse** | A misnamed review file that lands must be `git mv`'d; a denied write costs nothing. The check literally does not read content. | **Near zero.** No reconstruction needed. Add a `--name-only` mode. |
| `check-tasks-yaml.py` | PostToolUse (blocking) | Full-file YAML parse + `tasks_lib.validate_all` (schema/enums, depends_on DAG, slice naming, tick evidence) — `:85-95` | Full new content, parsed; plus repo state (unchanged by the write) | **PreToolUse** | Highest-value move. A malformed write corrupts the plan's single source of truth, and single-writer discipline (`agent-teams-pipeline.md`) means another agent may read it in the corrupt window. Exit 2 after the fact leaves the broken file on disk. | **Medium.** Needs a `loads(text)` in `tasks_lib` (2 lines) + Edit reconstruction. Keep PostToolUse as a backstop while it bakes. |
| `check-dead-contracts.py` | PostToolUse (blocking) | Every public `def` in a `storage_interfaces/`/`ports/` file has a `.method(` call site in `*interactors*`/`*app_interfaces*` (`:26-43`) | New content + repo-wide git grep (unaffected by the write) | **PreToolUse** (after the shim is proven) | Prevents a dead contract landing at all, which is what consumer-first actually asks for. | **Medium-high.** Sharper failure mode: today the file lands and the model writes the consumer then re-edits. On PreToolUse the file *cannot be created* until a consumer exists — doctrine-correct, but it turns a nudge into a wall. Move last. |
| `check-tick-evidence.py` | PostToolUse (blocking) | On legacy `tasks-*.md`: a `[x]` line has ≥1 backticked token resolving to a real path or a symbol in `*.py` (`:71-87`) | New content + repo state | PostToolUse is **acceptable**; PreToolUse marginally better | The artifact it protects is a *claim*, and the repair is a one-character untick — the cost of it landing is low. Its own docstring: YAML is "the single tasks format now"; this is a residual-markdown guard. | Low value either way. **Narrow the matcher instead.** |
| `check-task-ordering.py` | PostToolUse (blocking) | On legacy `tasks-*.md`: C1/C3/C5/C6 structural + slice-naming rules (`:84-141`) | New content only (no repo state) | Same as above | Same as above — legacy-markdown guard; `check-tasks-yaml.py` is the live enforcer. | Low value either way. **Narrow the matcher instead.** |

Non-blocking hooks, for completeness — all correctly placed:

| Hook | Event | Verdict |
|---|---|---|
| `ruff-check.sh` | PostToolUse async | **Correct.** It *mutates* the file (`ruff check --fix "$FILE_PATH"`) — it must run after the write exists. |
| `quality-gate.sh` | PostToolUse async | **Correct.** Advisory-only (always `exit 0`); greps the written file. |
| `check-orphaned-importers.py` | PostToolUse async + PreToolUse on `git commit` | **Correct, and the best-designed pair here.** It diffs the file against HEAD, so it needs the post-write state; and it *already* has a PreToolUse commit-gated mode (`--staged`) to catch `rm`-based deletions that emit no Edit event. |
| `check-duplicate-test-scaffolding.py` | PostToolUse async | **Correct.** Compares the written helper body against its HEAD version — needs post-write state. |
| `preflight-check.sh` | PreToolUse `if: Bash(git commit*)` | **Correct event, misleading output.** It prints "BLOCKING:" for staged GraphQL paths but ends `exit 0`, so it blocks nothing. Either drop the word or make it exit 2. |

---

## Recommendations, ordered by impact

### 1. Move the review **filename** check to PreToolUse (near-zero risk, do this first)

The filename rule reads only `tool_input.file_path`. Add a `--name-only` mode to `check-review-file.py` that
runs `is_review_file` + `in_feature_folder` + `FEATURE_NAME.match` and skips the four content checks. Leave the
existing PostToolUse entry for content.

```json
"PreToolUse": [
  {
    "matcher": "Edit|Write",
    "hooks": [
      {
        "type": "command",
        "if": "Edit(**/reviews/*-review.md)",
        "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/check-review-file.py --name-only"
      }
    ]
  }
]
```

### 2. Move `check-tasks-yaml.py` to PreToolUse, keeping PostToolUse as a backstop

Script changes: add `loads(text)` to `.claude/scripts/tasks_lib.py` beside `load(path)`; add a `--pre` mode to
the hook that builds candidate content from the payload (`content` for Write; disk + `old_string`→`new_string`
for Edit, honouring `replace_all`) and fails **open** if reconstruction is not possible. Then:

```json
"PreToolUse": [
  { "matcher": "Edit|Write", "hooks": [
    { "type": "command",
      "if": "Edit(**/tasks-ADR-*.yaml)",
      "command": "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/check-tasks-yaml.py --pre" }
  ]}
]
```

Keep the existing PostToolUse entry unchanged for a bake-in period — if the Edit reconstruction ever diverges
from real Edit semantics, the post-write pass catches it and the divergence shows up as a Pre-clean/Post-dirty
pair rather than as a silent miss. Drop the PostToolUse entry once no such pair has appeared.

**Known residual gap (unchanged by this):** `.claude/scripts/tasks.py tick` writes with `dump()` (line 101),
not the Edit tool, so no hook fires on that path at all. It is safe because it self-validates first
(`validate_all` at line 97). Any *other* non-Edit writer — a Bash heredoc, a Python script — bypasses both
events. That is an argument for keeping validation inside `tasks_lib`, which it already is.

### 3. Narrow all five with `if`, and watch the dedup hazard

Concrete `if` clauses (add to each existing PostToolUse entry; keep the in-script path filters as
defence-in-depth):

| Hook | `if` clause |
|---|---|
| `check-tasks-yaml.py` | `"Edit(**/tasks-ADR-*.yaml)"` |
| `check-review-file.py` | `"Edit(**/reviews/*-review.md)"` |
| `check-tick-evidence.py` | `"Edit(**/tasks-*.md)"` |
| `check-task-ordering.py` | `"Edit(**/tasks-*.md)"` |
| `check-dead-contracts.py` | `"Edit(**/*.py)"` — see caveat |

**The `check-dead-contracts` caveat.** It targets two directories, `storage_interfaces/` and `ports/`
(`CONTRACT_PATH`, `:25`). gitignore syntax has no brace alternation, so a precise filter needs **two** handler
entries — and the docs say command hooks are "deduplicated by command string and `args`", with no statement
that `if` is part of the key. Two entries with the same command and different `if` may silently collapse to
one. Two ways out: give each a distinguishing arg (`--scope storage_interfaces` / `--scope ports`), or use the
loose `Edit(**/*.py)` above and let the in-script regex do the precise work. The loose form still drops every
markdown/YAML/HTML edit and is the lower-risk option.

**A second false-positive surface worth closing while you are here.** `is_tasks_file` in both markdown hooks
is `(^|/)tasks-[^/]*\.md$` — which matches `.claude/proposals/tasks-json-implementation-plan.md`, a design doc,
not a plan. Both currently return `PASS` on it, so there is no live false positive; but an `if` clause scoped to
`**/docs/tasks/tasks-*.md` (the real home) removes the surface entirely.

### 4. Move `check-dead-contracts.py` to PreToolUse — last, and only after (2) proves the shim

Same `--pre` mechanics as `check-tasks-yaml.py`. Hold it until the Edit reconstruction has a track record,
because this hook's PreToolUse failure mode is the harshest of the five: it makes the interface file
un-creatable until its consumer exists. That is what consumer-first prescribes (`engineering-canon.md`, Law 2),
so it is defensible — but it is a behavioural change to how developers work, not just a timing change, and it
should be a deliberate decision rather than a side effect of an event swap.

### 5. Leave `check-tick-evidence.py` and `check-task-ordering.py` on PostToolUse

Narrow them per (3) and stop there. Both guard legacy markdown; `check-tasks-yaml.py` is the live enforcer for
the current format (their own docstrings say so). The repair cost for their findings is one character. Spending
Edit-reconstruction complexity on them is not worth it. Consider folding the two into one script — they share
`is_tasks_file` verbatim and both parse the same checklist lines — which halves the process count on markdown
tasks edits.

### 6. Fix `preflight-check.sh`'s "BLOCKING:" message

It prints `BLOCKING:` when staged files touch GraphQL paths, then `exit 0`. It is on the right event
(PreToolUse, `if: Bash(git commit*)`) and *could* block with exit 2. Either make it exit 2, or change the word
to `REMINDER:` so the output is not lying about what it does.

---

## Unverified / needs testing

1. **Does `if: "Edit(...)"` also gate a `Write` tool call?** The permissions doc says "(Edit rules cover all
   file-editing tools)" and warns that `Write(path)` rules are never matched — but that statement is about
   *permission checks*, and I am carrying it across to `if` evaluation by inference. Test: add
   `if: "Edit(**/tasks-ADR-*.yaml)"` to a no-op hook, then `Write` such a file and confirm it fired.
2. **Does `**/pattern` work inside `if`?** The hooks doc's only `if` file examples are `Edit(*.ts)` and
   `Edit(src/**)`, and it notes that a single-segment directory pattern in `if` matches only in the working
   directory. Bare-filename gitignore semantics ("match at any depth") come from the permissions doc. Every
   `if` clause proposed above should be smoke-tested against a file at real depth
   (`workflow_engine/docs/features/*/tasks/…`) before being trusted.
3. **Is `if` part of the hook dedup key?** Documented dedup is "by command string and `args`". Not stated
   either way for `if`. Blocks the two-entry form of Recommendation 3.
4. **Edit reconstruction fidelity.** `replace_all` semantics, multi-occurrence handling, and whether any other
   file-editing tool (`NotebookEdit`, or a multi-edit variant) can reach these paths under a `Edit|Write`
   matcher. Untested; this is the single largest risk in Recommendations 2 and 4, and the reason for the
   PostToolUse backstop.
5. **Exit-code semantics for non-tool events** (`Stop`, `TeammateIdle`, `TaskCompleted`). The doc excerpt I
   fetched gives the blocking table only for `PreToolUse`/`PostToolUse`. The recently-deleted
   `teammate-idle-check.sh` / `task-completed-check.sh` exited 2 on those events; I did not verify what exit 2
   means there, so I cannot say from documentation *why* they blocked agents from going idle — only that they
   ran a repo-wide `ruff check` and exited 2 (`.claude/hooks/teammate-idle-check.sh`,
   `.claude/hooks/task-completed-check.sh`, both still on disk but unwired).
6. **Whether `PostToolUse` fires on a *failed* tool call.** The doc lists a separate `PostToolUseFailure`
   event and describes `PostToolUse` as "After a tool call succeeds" — so a rejected/failed Edit presumably
   does not trigger the validators. Not tested; relevant only if a validator is ever expected to see a
   partial write.

---

## Measurements

Per-invocation no-op cost (payload pointing at a `.py` file none of them care about, mean of 3 runs, this
machine):

```
check-task-ordering:  21 ms
check-tick-evidence:  24 ms
check-dead-contracts: 24 ms
check-tasks-yaml:     31 ms   (imports PyYAML + tasks_lib)
check-review-file:    21 ms
```

Docs state matching hooks run in parallel, so the added wall clock per Edit/Write is roughly the slowest
(~31 ms), not the 121 ms sum. **Do not sell the `if` narrowing on speed** — sell it on the fact that five
interpreters currently start on every edit to a `.html`, a `.md`, or a `.json` for no reason, and each is a
place an unrelated edit can be wrongly blocked.
