# YAML-Source Task Breakdowns — Implementation Plan (Phases 1–2)

> **FORMAT UPDATE (2026-07-10):** tasks are **YAML** (`tasks-*.yaml`), not JSON — IDs quoted, PyYAML parser, validator ID-guard. Tasks 1–3 already reworked to YAML (`9da609c8ec`). Wherever a task below says `.json`, read `.yaml`; the hook is `check-tasks-yaml.py`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the standalone Python tooling that makes a JSON task-breakdown file the scriptable source of truth — a validator, a `tasks.py` CLI (read + core write ops), and a PostToolUse hook — with no pipeline wiring yet.

**Architecture:** One validation module (`tasks_lib.py`) holds schema + tick-evidence + dependency-first-ordering checks. `tasks.py` (CLI) and `check-tasks-json.py` (PostToolUse hook) both import it, so validation never diverges. The CLI does deterministic edits (tick/status) and reads (view/status/progress/series). Markdown is rendered on demand, never stored.

**Tech Stack:** Python 3 stdlib only (`json`, `argparse`, `re`, `sys`, `glob`, `subprocess`) — matches the existing hooks, zero new deps. pytest for tests.

## Global Constraints

- Python **stdlib only** — no new dependencies (mirrors existing `.claude/hooks/*.py`).
- Validation logic lives in **exactly one module** (`tasks_lib.py`); CLI and hook import it — never re-implement.
- **Additive:** do not modify `check-tick-evidence.py` or `check-task-ordering.py`; they keep serving markdown features.
- **Do not touch** the in-flight REF-001 feature's `tasks-*.md` files or any other dirty working-tree file. All new files land under `.claude/scripts/` and `.claude/hooks/`.
- Every task ends in a **commit**. Tests are **real** (pytest); the hook also carries a `--self-test` mode like the existing hooks.
- Per-task `artifacts` are **hand-authored**; `progress` weighting is **S=1 / M=2 / L=4**.
- Tick-evidence rule (carry over verbatim from `check-tick-evidence.py`): a task may be `status:"done"` only if ≥1 of its `artifacts` resolves to a real path OR a symbol found in tracked/untracked `*.py`. Docs don't count.

---

## File Structure

```
.claude/scripts/
  tasks_lib.py        schema + validation (load, validate_schema, check_tick_evidence,
                      check_ordering, compute_ordering, render_markdown, progress) — pure functions
  tasks.py            CLI (argparse) — imports tasks_lib; sub-commands
  tests/
    test_tasks_lib.py    unit tests for the library
    test_tasks_cli.py    CLI integration tests (subprocess or main())
    fixtures/
      valid.json         a filled 2-slice example (the golden schema example)
      bad_*.json         invalid fixtures (one per failure mode)
.claude/hooks/
  check-tasks-json.py    PostToolUse wrapper: reads stdin JSON, skips non tasks-*.json,
                         calls tasks_lib, exit 2 + stderr on violation; --self-test mode
.claude/skills/task-breakdown/references/
  tasks-schema.json      the schema-as-doc + inline field comments (Phase 3 consumes it;
                         created here as the validation contract)
```

`tasks_lib.py` is the one unit everything else depends on — keep it pure (functions take parsed dict + base dir, return findings; no I/O except the artifact-existence check).

---

## Task 1: Schema doc + golden example fixture

**Files:**
- Create: `.claude/skills/task-breakdown/references/tasks-schema.json`
- Create: `.claude/scripts/tests/fixtures/valid.json`

**Interfaces:**
- Produces: the canonical field set every later task validates against — feature-level `{adr, module?, what?, tasks[], carried_flags[], decisions[]}`; per-task `{id, type, status, outcome, user_stories[], depends_on[], inputs, output, outline, cases[], size, tier, artifacts[], commit}`.

- [ ] **Step 1: Write `tasks-schema.json`** — a JSON document describing the schema with a `"$comment"` per field (human/LLM-readable contract; not JSON-Schema-validated, just the reference). Enumerate: `type ∈ [slice,foundation,task,composition,refactor]`, `status ∈ [todo,in_progress,done]`, `size ∈ [S,M,L]`, `tier ∈ [mechanical,judgment]`. Mark required vs optional (`module`, `what`, `commit` optional).

- [ ] **Step 2: Write `fixtures/valid.json`** — a real 2-slice example (foundation 1.0 → slice 2.0 with tasks 2.1–2.3 incl. one contract task others `depends_on`, plus a `composition` and the slice's integration task). Every enum exercised, one `done` task with a real repo artifact (e.g. `common/exceptions.py`), the rest `todo`.

- [ ] **Step 3: Eyeball-validate** — `python3 -c "import json; json.load(open('.claude/scripts/tests/fixtures/valid.json'))"` → no error.

- [ ] **Step 4: Commit**
```bash
git add .claude/skills/task-breakdown/references/tasks-schema.json .claude/scripts/tests/fixtures/valid.json
git commit -m "feat(tasks): JSON task schema doc + golden example fixture"
```

---

## Task 2: `tasks_lib.load` + `validate_schema`

**Files:**
- Create: `.claude/scripts/tasks_lib.py`
- Test: `.claude/scripts/tests/test_tasks_lib.py`
- Create: `.claude/scripts/tests/fixtures/bad_enum.json`, `bad_missing_field.json`, `bad_dup_id.json`

**Interfaces:**
- Produces: `load(path) -> dict` (raises `TasksError` on bad JSON); `validate_schema(data) -> list[str]` (returns findings, empty = ok). `TasksError(Exception)`.

- [ ] **Step 1: Write failing tests**
```python
# test_tasks_lib.py
import json, pathlib, pytest
from tasks_lib import load, validate_schema, TasksError
FIX = pathlib.Path(__file__).parent / "fixtures"

def test_valid_fixture_passes_schema():
    assert validate_schema(load(FIX / "valid.json")) == []

def test_bad_enum_reported():
    findings = validate_schema(load(FIX / "bad_enum.json"))
    assert any("tier" in f for f in findings)

def test_missing_required_field_reported():
    findings = validate_schema(load(FIX / "bad_missing_field.json"))
    assert any("outcome" in f for f in findings)

def test_duplicate_id_reported():
    findings = validate_schema(load(FIX / "bad_dup_id.json"))
    assert any("duplicate" in f.lower() for f in findings)

def test_load_bad_json_raises():
    with pytest.raises(TasksError):
        load(FIX / "does_not_exist.json")
```

- [ ] **Step 2: Create the `bad_*.json` fixtures** — copy `valid.json`, then: `bad_enum` sets a task `"tier":"frontier"`; `bad_missing_field` deletes a task's `outcome`; `bad_dup_id` gives two tasks the same `id`.

- [ ] **Step 3: Run — expect fail** — `cd .claude/scripts && python3 -m pytest tests/test_tasks_lib.py -v` → FAIL (module missing).

- [ ] **Step 4: Implement `load` + `validate_schema`**
```python
# tasks_lib.py
import json
class TasksError(Exception): ...
TYPES={"slice","foundation","task","composition","refactor"}
STATUS={"todo","in_progress","done"}; SIZE={"S","M","L"}; TIER={"mechanical","judgment"}
REQ_TASK={"id","type","status","outcome","user_stories","depends_on","inputs","output","outline","cases","size","tier","artifacts"}
def load(path):
    try: return json.loads(open(path).read())
    except (OSError, ValueError) as e: raise TasksError(f"{path}: {e}")
def validate_schema(data):
    out=[]; ids=set()
    if "adr" not in data: out.append("feature: missing 'adr'")
    for t in data.get("tasks",[]):
        tid=t.get("id","?")
        for f in REQ_TASK-set(t): out.append(f"task {tid}: missing '{f}'")
        if t.get("type") not in TYPES: out.append(f"task {tid}: bad type {t.get('type')!r}")
        if t.get("status") not in STATUS: out.append(f"task {tid}: bad status")
        if t.get("size") not in SIZE: out.append(f"task {tid}: bad size")
        if t.get("tier") not in TIER: out.append(f"task {tid}: bad tier {t.get('tier')!r}")
        if tid in ids: out.append(f"task {tid}: duplicate id"); ids.add(tid)
        else: ids.add(tid)
    return out
```

- [ ] **Step 5: Run — expect pass** — same pytest command → PASS.

- [ ] **Step 6: Commit**
```bash
git add .claude/scripts/tasks_lib.py .claude/scripts/tests/test_tasks_lib.py .claude/scripts/tests/fixtures/bad_*.json
git commit -m "feat(tasks): load + schema validation in tasks_lib"
```

---

## Task 3: `check_tick_evidence`

**Files:**
- Modify: `.claude/scripts/tasks_lib.py`
- Modify: `.claude/scripts/tests/test_tasks_lib.py`
- Create: `.claude/scripts/tests/fixtures/bad_tick_no_evidence.json`

**Interfaces:**
- Consumes: `load`, task `artifacts[]`, task `status`.
- Produces: `check_tick_evidence(data, base_dir) -> list[str]` — a `done` task with no resolvable artifact is a finding. Reuses the existing hook's rule: an artifact resolves if it's an existing path OR a symbol grep-found in tracked/untracked `*.py`.

- [ ] **Step 1: Write failing tests**
```python
from tasks_lib import check_tick_evidence
import os
def test_done_task_with_real_artifact_passes():
    assert check_tick_evidence(load(FIX/"valid.json"), os.getcwd()) == []
def test_done_task_without_evidence_flagged():
    findings = check_tick_evidence(load(FIX/"bad_tick_no_evidence.json"), os.getcwd())
    assert any("evidence" in f.lower() for f in findings)
```

- [ ] **Step 2: Create `bad_tick_no_evidence.json`** — copy `valid.json`, set a task `"status":"done"` with `"artifacts":["totally/made/up/path.py","NoSuchSymbol"]`.

- [ ] **Step 3: Run — expect fail.** `python3 -m pytest tests/test_tasks_lib.py::test_done_task_without_evidence_flagged -v`

- [ ] **Step 4: Implement `check_tick_evidence`** — port the resolution logic from `.claude/hooks/check-tick-evidence.py` (path-exists OR symbol in `git ls-files`/untracked `*.py`). Loop `done` tasks; a task with zero resolving artifacts → `f"task {id}: done but no artifact resolves (evidence)"`.
```python
import os, re, subprocess
IDENT=re.compile(r"^@?[A-Za-z_][A-Za-z0-9_.]*(\(\))?$")
def _resolves(tok, base):
    if os.path.exists(os.path.join(base, tok)): return True
    if IDENT.match(tok):
        sym=tok.rstrip("()").split(".")[-1]
        try:
            r=subprocess.run(["grep","-rl","--include=*.py",sym,base],capture_output=True,text=True,timeout=20)
            return bool(r.stdout.strip())
        except Exception: return False
    return False
def check_tick_evidence(data, base_dir):
    out=[]
    for t in data.get("tasks",[]):
        if t.get("status")=="done" and not any(_resolves(a,base_dir) for a in t.get("artifacts",[])):
            out.append(f"task {t.get('id')}: done but no artifact resolves (evidence)")
    return out
```

- [ ] **Step 5: Run — expect pass.**

- [ ] **Step 6: Commit**
```bash
git add .claude/scripts/tasks_lib.py .claude/scripts/tests/test_tasks_lib.py .claude/scripts/tests/fixtures/bad_tick_no_evidence.json
git commit -m "feat(tasks): tick-evidence check (done requires real artifact)"
```

---

## Task 4: `check_ordering` + `compute_ordering`

**Files:**
- Modify: `.claude/scripts/tasks_lib.py`
- Modify: `.claude/scripts/tests/test_tasks_lib.py`
- Create: `.claude/scripts/tests/fixtures/bad_cycle.json`, `bad_forward_dep.json`

**Interfaces:**
- Produces: `check_ordering(data) -> list[str]` (findings: unknown `depends_on` id, cycle, a task done while a dep is not done); `compute_ordering(data) -> {"sequence": [...], "parallel": [[...]]}` (topological layers → the `∥` sets, replacing the stored footer).

- [ ] **Step 1: Write failing tests**
```python
from tasks_lib import check_ordering, compute_ordering
def test_valid_ordering_passes():
    assert check_ordering(load(FIX/"valid.json")) == []
def test_cycle_flagged():
    assert any("cycle" in f.lower() for f in check_ordering(load(FIX/"bad_cycle.json")))
def test_unknown_dep_flagged():
    assert any("unknown" in f.lower() for f in check_ordering(load(FIX/"bad_forward_dep.json")))
def test_compute_parallel_groups_independent_tasks():
    par = compute_ordering(load(FIX/"valid.json"))["parallel"]
    assert isinstance(par, list)
def test_done_before_dep_done_flagged():
    d=load(FIX/"valid.json")
    # mark a task done whose dep is still todo
    ...  # (construct in-test) 
```

- [ ] **Step 2: Create fixtures** — `bad_cycle`: two tasks `depends_on` each other; `bad_forward_dep`: a task `depends_on` an id that doesn't exist.

- [ ] **Step 3: Run — expect fail.**

- [ ] **Step 4: Implement** — build id→task map; findings for (a) any `depends_on` id not in the map ("unknown"), (b) a cycle (DFS colouring), (c) a `done` task with a non-`done` dependency ("done before its dependency"). `compute_ordering`: Kahn's algorithm; each layer of the topo sort with >1 member is a `parallel` group.
```python
def check_ordering(data):
    out=[]; tasks={t["id"]:t for t in data.get("tasks",[])}
    for t in data.get("tasks",[]):
        for d in t.get("depends_on",[]):
            if d not in tasks: out.append(f"task {t['id']}: unknown depends_on {d!r}")
            elif t.get("status")=="done" and tasks[d].get("status")!="done":
                out.append(f"task {t['id']}: done before its dependency {d}")
    # cycle detection
    WHITE,GREY,BLACK=0,1,2; color={i:WHITE for i in tasks}
    def dfs(i):
        color[i]=GREY
        for d in tasks[i].get("depends_on",[]):
            if d not in tasks: continue
            if color[d]==GREY: return True
            if color[d]==WHITE and dfs(d): return True
        color[i]=BLACK; return False
    if any(color[i]==WHITE and dfs(i) for i in tasks): out.append("ordering: dependency cycle")
    return out
```
(Implement `compute_ordering` with Kahn's algorithm returning `{"sequence":[...], "parallel":[[...]]}`.)

- [ ] **Step 5: Run — expect pass.**

- [ ] **Step 6: Commit** — `feat(tasks): dependency-first ordering check + computed parallelism`

---

## Task 5: `validate_all` aggregator + `tasks.py validate`

**Files:**
- Modify: `.claude/scripts/tasks_lib.py` (add `validate_all(data, base_dir) -> list[str]`)
- Create: `.claude/scripts/tasks.py`
- Create: `.claude/scripts/tests/test_tasks_cli.py`

**Interfaces:**
- Produces: `validate_all` = schema + tick-evidence + ordering concatenated. CLI `tasks.py validate <file>` → exit 0 + "OK" or exit 1 + findings.

- [ ] **Step 1: Write failing CLI test**
```python
# test_tasks_cli.py
import subprocess, sys, pathlib
CLI=pathlib.Path(__file__).parents[1]/"tasks.py"; FIX=pathlib.Path(__file__).parent/"fixtures"
def run(*a): return subprocess.run([sys.executable,str(CLI),*a],capture_output=True,text=True)
def test_validate_ok():
    r=run("validate",str(FIX/"valid.json")); assert r.returncode==0
def test_validate_bad():
    r=run("validate",str(FIX/"bad_enum.json")); assert r.returncode==1 and "tier" in r.stdout
```

- [ ] **Step 2: Run — expect fail.**

- [ ] **Step 3: Implement `validate_all` + `tasks.py` argparse skeleton** with the `validate` sub-command wired to `validate_all`. `sys.path` insert so `tasks.py` imports `tasks_lib`.

- [ ] **Step 4: Run — expect pass.**

- [ ] **Step 5: Commit** — `feat(tasks): tasks.py CLI skeleton + validate command`

---

## Task 6: `tasks.py view` (render markdown on demand)

**Files:**
- Modify: `.claude/scripts/tasks_lib.py` (add `render_markdown(data) -> str`)
- Modify: `.claude/scripts/tasks.py` (add `view` sub-command)
- Modify: `.claude/scripts/tests/test_tasks_lib.py`

**Interfaces:**
- Produces: `render_markdown(data)` → the checkbox view (`- [x]`/`- [ ] N.N type: outcome (US-…) [size/tier]`, indented by depth, followed by cases/✔; footer = computed ordering + carried_flags + decisions). `tasks.py view <file>` prints it.

- [ ] **Step 1: Write failing test** — `render_markdown(load(valid))` contains `- [x]` for the done task, `- [ ]` for a todo, the outcome text, and a `Cases:` line.
- [ ] **Step 2: Run — expect fail.**
- [ ] **Step 3: Implement** `render_markdown` (pure string build; `done→[x]`) and the `view` command.
- [ ] **Step 4: Run — expect pass.**
- [ ] **Step 5: Commit** — `feat(tasks): on-demand markdown view (tasks.py view)`

---

## Task 7: `tasks.py status` + `progress`

**Files:**
- Modify: `.claude/scripts/tasks_lib.py` (add `progress(data) -> dict`)
- Modify: `.claude/scripts/tasks.py` (add `status`, `progress` sub-commands)
- Modify: `.claude/scripts/tests/test_tasks_lib.py`

**Interfaces:**
- Produces: `progress(data)` → `{"raw": (done,total), "weighted": (wdone,wtotal)}` with **S=1,M=2,L=4**. `status` prints per-task id+status; `progress` prints the two ratios + %.

- [ ] **Step 1: Write failing test** — `progress(load(valid))["weighted"]` sums the right weights; done-count matches the fixture.
- [ ] **Step 2: Run — expect fail.**
- [ ] **Step 3: Implement** `progress` (`W={"S":1,"M":2,"L":4}`) + the two commands.
- [ ] **Step 4: Run — expect pass.**
- [ ] **Step 5: Commit** — `feat(tasks): status + weighted progress (S1/M2/L4)`

---

## Task 8: Write ops — `tick` / `untick` / `set-status` (revalidate inline)

**Files:**
- Modify: `.claude/scripts/tasks_lib.py` (add `set_status(data, id, status) -> data`)
- Modify: `.claude/scripts/tasks.py` (sub-commands `tick`/`untick`/`set-status`)
- Modify: `.claude/scripts/tests/test_tasks_cli.py`

**Interfaces:**
- Consumes: `load`, `validate_all`, `set_status`.
- Produces: `tick <file> <id>` sets status `done` **only if** `validate_all` on the result passes (fail-closed: refuse + exit 1, leave file untouched); writes back pretty-printed JSON. `untick` → `todo`; `set-status <file> <id> <status>`.

- [ ] **Step 1: Write failing CLI tests** — copy `valid.json` to a tmp file (pytest `tmp_path`); `tick` an existing `todo` task whose deps are done → exit 0, re-load shows `done`. `tick` a task with a fake artifact → exit 1 (evidence fail), file unchanged. `tick` unknown id → exit 1.
```python
def test_tick_valid(tmp_path):
    import shutil; f=tmp_path/"t.json"; shutil.copy(FIX/"valid.json",f)
    # pick a todo task with real artifacts + done deps, tick it
    r=run("tick",str(f),"<id>"); assert r.returncode==0
    import json; assert json.load(open(f))  # status done for <id>
```
- [ ] **Step 2: Run — expect fail.**
- [ ] **Step 3: Implement** — load → `set_status` on a copy → `validate_all` → if clean write back (`json.dumps(indent=2, ensure_ascii=False)`), else print findings + exit 1 (no write). Unknown id → exit 1.
- [ ] **Step 4: Run — expect pass.**
- [ ] **Step 5: Commit** — `feat(tasks): tick/untick/set-status with fail-closed revalidation`

---

## Task 9: `tasks.py series` (commit series from `commit` fields)

**Files:**
- Modify: `.claude/scripts/tasks.py` (add `series`)
- Modify: `.claude/scripts/tests/test_tasks_cli.py`

**Interfaces:**
- Produces: `series <file>` → one line per task with a non-null `commit`: `<hash> · <outcome> · <artifacts joined>`. (The push-gate commit-series.)

- [ ] **Step 1: Write failing test** — a fixture task with `"commit":"abc1234"` appears in `series` output; null-commit tasks don't.
- [ ] **Step 2: Run — expect fail.**
- [ ] **Step 3: Implement** `series`.
- [ ] **Step 4: Run — expect pass.**
- [ ] **Step 5: Commit** — `feat(tasks): series command (push-gate commit list)`

---

## Task 10: PostToolUse hook `check-tasks-json.py` + wire in settings.json

**Files:**
- Create: `.claude/hooks/check-tasks-json.py`
- Modify: `.claude/settings.json` (PostToolUse, matcher `Edit|Write`, guard on `tasks-*.json`)

**Interfaces:**
- Consumes: `tasks_lib.load` + `validate_all` (import via `sys.path` insert of `../scripts`).
- Produces: hook contract — reads PostToolUse JSON on stdin, extracts `tool_input.file_path`; if it doesn't match `tasks-.*\.json$` → exit 0; else `validate_all` → exit 2 + stderr findings on violation, exit 0 clean. `--self-test` runs the golden + one bad fixture (mirrors `check-tick-evidence.py`).

- [ ] **Step 1: Write the hook** — stdin JSON parse, path filter regex `(^|/)tasks-[^/]*\.json$`, import `tasks_lib`, run `validate_all` with `base_dir=CLAUDE_PROJECT_DIR`, exit 2 + stderr on findings. Add `--self-test`: assert `valid.json` clean and `bad_enum.json` flagged; print "self-test OK".

- [ ] **Step 2: Run the self-test** — `python3 .claude/hooks/check-tasks-json.py --self-test` → prints OK, exit 0.

- [ ] **Step 3: Simulate a hook call**
```bash
echo '{"tool_input":{"file_path":".claude/scripts/tests/fixtures/bad_enum.json"}}' | python3 .claude/hooks/check-tasks-json.py; echo "exit=$?"
```
Expected: stderr lists the `tier` finding, `exit=2`.

- [ ] **Step 4: Wire in `settings.json`** — add to `PostToolUse` `Edit|Write` a `check-tasks-json.py` entry (after the existing hooks). Validate JSON: `python3 -c "import json;json.load(open('.claude/settings.json'))"`.

- [ ] **Step 5: Full suite green** — `cd .claude/scripts && python3 -m pytest -v` → all pass.

- [ ] **Step 6: Commit**
```bash
git add .claude/hooks/check-tasks-json.py .claude/settings.json
git commit -m "feat(tasks): PostToolUse validator hook for tasks-*.json + wiring"
```

---

## Phase 1–2 Done Criteria
- `python3 -m pytest .claude/scripts/tests -v` all green.
- `python3 .claude/hooks/check-tasks-json.py --self-test` OK.
- `tasks.py validate|view|status|progress|tick|untick|set-status|series` all work on `valid.json`.
- Existing markdown hooks untouched; no pipeline file (skill/agent/rule) modified yet.

## Follow-on (Phase 3–5) — separate plan, after this lands
- **Phase 3 Authoring:** rewrite `.claude/skills/task-breakdown/SKILL.md` + `references/tasks-file-template.md` to emit JSON against `tasks-schema.json`; first NEW feature exercises it.
- **Phase 4 Integration:** `task-coordinator.md` ticks via `tasks.py` (sole-writer holds JSON); update `dev-loop.md`, `agent-teams-pipeline.md`, `feature-folder.md`, `feature-context.md`, `feature-status`.
- **Phase 5 Rare ops:** `tasks.py add` (JSON on stdin) + `reorder` (renumber + re-point `depends_on`).
