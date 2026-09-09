import copy
import os
import re
import subprocess

import yaml


class TasksError(Exception):
    ...


IDENTIFIER = re.compile(r"^@?[A-Za-z_][A-Za-z0-9_.]*(\(\))?$")


def _resolves(tok, base):
    # Mirror .claude/hooks/check-tick-evidence.py exactly (must-mirror constraint):
    # path-exists OR symbol in *.py via `git grep --untracked` (git-scoped, so
    # gitignored vendor code like venv/ never counts as evidence).
    if os.path.exists(os.path.join(base, tok)):
        return True
    if IDENTIFIER.match(tok):
        name = tok.lstrip("@").rstrip("()").split(".")[0]
        if not name or len(name) < 3:
            return True  # too generic to falsify — don't block on it
        try:
            result = subprocess.run(
                [
                    "git",
                    "grep",
                    "-l",
                    "--untracked",
                    "--fixed-strings",
                    name,
                    "--",
                    "*.py",
                ],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=base,
            )
        except (OSError, subprocess.TimeoutExpired):
            return True  # tooling unavailable — never false-block
        return result.returncode == 0
    return False


def check_tick_evidence(data, base_dir):
    out = []
    for t in data.get("tasks", []):
        if t.get("status") == "done" and not any(
            _resolves(a, base_dir) for a in t.get("artifacts", [])
        ):
            out.append(
                f"task {t.get('id')}: done but no artifact resolves (evidence)"
            )
    return out


TYPES = {"slice", "foundation", "task", "composition", "refactor"}
STATUS = {"todo", "in_progress", "done"}
SIZE = {"S", "M", "L"}
TIER = {"mechanical", "judgment"}
REQ_TASK = {
    "id",
    "type",
    "status",
    "outcome",
    "user_stories",
    "depends_on",
    "inputs",
    "output",
    "outline",
    "cases",
    "size",
    "tier",
    "artifacts",
}


def load(path):
    try:
        return yaml.safe_load(open(path).read())
    except (OSError, yaml.YAMLError) as e:
        raise TasksError(f"{path}: {e}")


def dump(data, path):
    with open(path, "w") as f:
        yaml.safe_dump(
            data,
            f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )


def set_status(data, id, status):
    updated = copy.deepcopy(data)
    for t in updated.get("tasks", []):
        if t.get("id") == id:
            t["status"] = status
            return updated
    raise TasksError(f"unknown task id: {id!r}")


LAYER_NOUN = re.compile(
    r"^(?:(?:create|add|set ?up|build|define|implement|write)\s+)?(?:the\s+)?"
    r"(?:storages?(?:\s+layer)?|storage\s+interfaces?(?:\s*&\s*implementations?)?"
    r"|interactors?|adapters?|helpers?|utils?|services?)$",
    re.I,
)


def _outcome_head(outcome):
    # Classify on the outcome head only — a trailing "(ADR §5)" or "— note" is not
    # part of the name. Mirrors check-task-ordering.py's title_head().
    cleaned = str(outcome or "").replace("`", "")
    return re.split(r"\s+\(|\s+[—–-]{1,2}\s+", cleaned, maxsplit=1)[0].strip()


def check_slice_naming(data):
    # Ports check-task-ordering.py C1/C5/C6 to the YAML format: a slice/foundation
    # parent's `outcome` must be a caller-nameable behaviour, never a bare layer noun
    # ("Storages", "Interactors", "Adapters"). Layer ORDER (the old C2/C3) is now
    # just the authored depends_on graph — check_ordering enforces the stated
    # dependencies (consumer-first when authored so), not a fixed layer order;
    # consumer-owns-contract (the old C4 citation) is check-dead-contracts.py at
    # code write-time.
    out = []
    for t in data.get("tasks", []):
        if t.get("type") in {"slice", "foundation"} and LAYER_NOUN.match(
            _outcome_head(t.get("outcome"))
        ):
            out.append(
                f"task {t.get('id')}: outcome {t.get('outcome')!r} is a bare layer noun — "
                f"name it a caller-nameable behaviour, not a code layer "
                f"(engineering-canon: vertical slicing/INVEST)"
            )
    return out


def check_ordering(data):
    # Pure depends_on DAG safety: unknown deps, done-before-dependency, cycles.
    # It intentionally does NOT mandate a layer ORDER — consumer-first
    # (engineering-canon Law 1: interactor built first, drives out its interface;
    # impl + integration closer depend_on the interactor) is a VALID shape here by
    # construction. Consumer-owns-contract is enforced at code-write time by
    # check-dead-contracts.py (an interface method with no consumer is blocked),
    # not by any ordering rule in this file. Reversing this to re-enforce a
    # door-last layer order would reintroduce the classifier the 2026-07-11 ruling
    # removed — keep it a plain dependency graph.
    out = []
    tasks = {t["id"]: t for t in data.get("tasks", [])}
    for t in data.get("tasks", []):
        for dep_id in t.get("depends_on", []):
            if dep_id not in tasks:
                out.append(f"task {t['id']}: unknown depends_on {dep_id!r}")
            elif (
                t.get("status") == "done"
                and tasks[dep_id].get("status") != "done"
            ):
                out.append(
                    f"task {t['id']}: done before its dependency {dep_id}"
                )
    if _has_cycle(tasks):
        out.append("ordering: dependency cycle")
    return out


def _has_cycle(tasks):
    WHITE, GREY, BLACK = 0, 1, 2
    color = {task_id: WHITE for task_id in tasks}

    def dfs(task_id):
        color[task_id] = GREY
        for dep_id in tasks[task_id].get("depends_on", []):
            if dep_id not in tasks:
                continue
            if color[dep_id] == GREY:
                return True
            if color[dep_id] == WHITE and dfs(dep_id):
                return True
        color[task_id] = BLACK
        return False

    return any(color[task_id] == WHITE and dfs(task_id) for task_id in tasks)


def compute_ordering(data):
    tasks = {t["id"]: t for t in data.get("tasks", [])}
    remaining_deps = {
        task_id: {d for d in t.get("depends_on", []) if d in tasks}
        for task_id, t in tasks.items()
    }
    sequence = []
    parallel = []
    resolved = set()
    while len(resolved) < len(tasks):
        layer = sorted(
            task_id
            for task_id, deps in remaining_deps.items()
            if task_id not in resolved and deps <= resolved
        )
        if not layer:
            break  # cycle present — check_ordering reports it, avoid infinite loop
        sequence.extend(layer)
        if len(layer) > 1:
            parallel.append(layer)
        resolved.update(layer)
    return {"sequence": sequence, "parallel": parallel}


def validate_all(data, base_dir):
    return (
        validate_schema(data)
        + check_tick_evidence(data, base_dir)
        + check_ordering(data)
        + check_slice_naming(data)
    )


# --- Readability (WARN-level — deliberately NOT in validate_all) --------------
#
# WHY warn and not block: validate_all findings exit 2 and refuse the write, which
# would stall an in-flight feature on its next tick. So this reports and lets the
# write through. FLIP TO BLOCKING once the live files sit under budget; the flip is
# one line (add check_readability(data) to validate_all) and is logged in dhruva
# memory.
#
# The outline cap was re-fitted 2026-07-20 (300 -> 900, L-exception dropped) after
# measuring all 85 live outlines: the old cap flagged 91% of them. That is the
# lesson worth keeping — a threshold nearly every instance violates has stopped
# being a limit and become noise. Re-measure before re-tuning, never guess.
#
# WHY it exists at all: the caps and the plain-words rule were already prose in
# task-breakdown/SKILL.md and plain-language.md, and prose lost — two words banned
# in plain-language.md ("steel thread", "load-bearing") shipped in live files, from
# this config's own skills. A banned-word table that nothing checks is a wish.

# Nicknames: metaphors coined inside one feature for a thing with a real name.
# There is nowhere to look them up. Project vocabulary with a defined home
# ("slice", "integration closer", "consumer-first", "build-once") is NOT here —
# the test is "can the reader look it up?", not "is it a term?".
NICKNAMES = {
    "the door": "name the interactor (e.g. ExecuteTransitionInteractor)",
    "a press": "'a transition attempt' / 'when someone tries to move an item'",
    "the press": "'the transition attempt'",
    "the walk": "'the guard evaluator'",
    "umbrella row": "'the slice's parent row'",
    "the battery": "'the set of guards'",
    "the diary": "name the actual record (an audit log? a state record?)",
    "steel thread": "'the first thin end-to-end path'",
    "load-bearing": "'it matters because ...' / 'it holds up ...'",
    "second pass": "'a second read' / 'the second time it runs'",
    "reconstitution": "'build the objects (from the stored rows)'",
    "orchestration layer": "'the part that runs the steps in order'",
    "byte-match": "'same behaviour as today'",
}

# Caps per the Field length budget in task-breakdown/SKILL.md. An over-budget
# outline is the tell that WHY leaked into WHAT — the ADR owns WHY, and it is
# linked ("see ADR §N"), never pasted.
# Re-fitted 2026-07-20 against the 85 live outlines (was 300, with a 500 special
# case for size L). Two things the measurement showed:
#   1. 300 flagged 91% of tasks. A detector that fires on nearly everything cannot
#      discriminate leaked-WHY from a legitimately dense judgment task — it is
#      noise, and readers learn to scroll past it. Median is 664, p90 is 1,936.
#   2. `size` does NOT predict outline length — S median 676, M median 670,
#      L median 539. The L exception was INVERTED (it gave the extra room to the
#      tasks that needed it least), so it is gone rather than re-tuned.
# 900 flags roughly the top third — the 1,900-3,000 char outlines that really are
# an essay pasted into a field, which is the shape this check exists to catch.
FIELD_CAPS = {"outcome": 120, "output": 120, "outline": 900}

# Positional citations: `ADR-002 D8`, `US-11 AC5`. The ordinal is not identity —
# it shifts on any insert/renumber and nothing breaks. Three such pointers rotted
# on REF-001; one later resolved to a real-but-WRONG decision once that number was
# legitimately reused. Warn only: the checker cannot tell a fresh pointer from a
# rotted one, so this flags the FORM, and plain-language.md owns the fix.
POSITIONAL_CITE = re.compile(r"\badr-\d+\s+d\d+\b|\bus-\d+\s+ac\d+\b", re.I)

# `inputs`/`output` are a SIGNATURE (types in -> type out), not a reading list.
# Everything below already has its own home, so it is duplication wherever it
# appears here: a path -> artifacts; a task id -> depends_on; a story id ->
# user_stories; an ADR ref -> the top-level `adr` + outline's link.
NOT_A_TYPE = (
    (re.compile(r"/"), "a path — paths live in `artifacts`"),
    (re.compile(r"\.(py|md|yaml)\b"), "a file — paths live in `artifacts`"),
    (re.compile(r"\bUS-\d"), "a story id — that's `user_stories`"),
    (
        re.compile(r"\bADR\b|§"),
        "an ADR reference — that's the top-level `adr` + `outline`'s link",
    ),
    (re.compile(r"^\d+\.\d+$"), "a task id — that's `depends_on`"),
)
# A type name is not a sentence. `List[GuardResult]` is 1 word; "the guard built
# in task 1.1" is 6. Four is generous headroom for `Optional[Dict[str, Guard]]`.
MAX_TYPE_WORDS = 4
# The measured tell of a bloated outcome: a second thought after an em-dash.
# It belongs in `outline`.
OUTCOME_ELABORATION = re.compile(r"\s[—–]\s")

# A blocker stated in PROSE is invisible to check_ordering, which only reads
# `depends_on`. On the relieve-v2 plan a task carried "BLOCKED IF STEP 6 HAS NOT
# LANDED" in its own outline while sitting three positions EARLIER in the queue —
# so the slice closed APPROVED with an unbuildable task inside it. Warn only: the
# checker cannot tell which task is meant, so it flags the FORM and the fix is
# always the same — make it a `depends_on` edge, then delete the sentence.
PROSE_BLOCKER = re.compile(
    # NOT "blocked by": that form usually describes a mechanism ("blocked by the
    # duplicate-scaffolding hook"), not a task order — it measured as the only
    # false positive across the 8 relieve-v2 files.
    r"\bblocked\s+(?:if|on|until)\b|\bdo not start (?:until|before)\b"
    r"|\brequires step \d|\bafter step \d+ (?:has )?land",
    re.I,
)


def _signature_findings(tid, field, value):
    out = []
    for pattern, why in NOT_A_TYPE:
        if pattern.search(value):
            out.append(
                f"task {tid}: {field} {value[:60]!r} is {why} — name the TYPE instead"
            )
            return out  # one finding per entry is enough
    if len(value.split()) > MAX_TYPE_WORDS:
        out.append(
            f"task {tid}: {field} {value[:60]!r} reads as prose — {field} is a signature "
            f"(the type the code {'consumes' if field == 'inputs' else 'produces'}), not a description"
        )
    return out


def check_readability(data):
    """Warn-level: field budget + nickname denylist + signature shape."""
    out = []
    for t in data.get("tasks", []):
        tid = t.get("id", "?")
        outcome = t.get("outcome")
        if isinstance(outcome, str) and OUTCOME_ELABORATION.search(outcome):
            out.append(
                f"task {tid}: outcome elaborates after an em-dash — outcome is one clause "
                f"(what becomes true when done); the second thought belongs in `outline`"
            )
        inputs = t.get("inputs")
        if isinstance(inputs, list):
            for entry in inputs:
                if isinstance(entry, str) and entry.strip():
                    out += _signature_findings(tid, "inputs", entry.strip())
        output = t.get("output")
        if isinstance(output, str) and output.strip():
            out += _signature_findings(
                tid, "output", output.strip().strip("`")
            )
        for field, cap in FIELD_CAPS.items():
            value = t.get(field)
            if not isinstance(value, str):
                continue
            if len(value) > cap:
                out.append(
                    f"task {tid}: {field} is {len(value)} chars (budget {cap}) — "
                    f"cut the reasoning and link the ADR ('see ADR §N'); keep the instruction"
                )
        haystack = " ".join(
            v.lower()
            for f in ("outcome", "inputs", "output", "outline")
            for v in ([t[f]] if isinstance(t.get(f), str) else t.get(f) or [])
            if isinstance(v, str)
        )
        for nickname, better in sorted(NICKNAMES.items()):
            if nickname in haystack:
                out.append(
                    f"task {tid}: {nickname!r} is a nickname a reader cannot look up — {better} "
                    f"(plain-language.md)"
                )
        for match in sorted(set(POSITIONAL_CITE.findall(haystack))):
            out.append(
                f"task {tid}: {match!r} cites by position — ordinals shift on any "
                f"insert or renumber, silently re-pointing the citation. Name the "
                f"decision/criterion instead (plain-language.md, Stable citations)"
            )
        if isinstance(t.get("inputs"), str):
            out.append(
                f"task {tid}: inputs is a paragraph — author it as a list, one thing per line "
                f"(tasks-schema.yaml; legacy string form still validates)"
            )
        if PROSE_BLOCKER.search(haystack):
            out.append(
                f"task {tid}: states a blocker in prose — a blocker the ordering check "
                f"cannot see is not a blocker. Make it a `depends_on` edge on the task "
                f"it waits for, then delete the sentence"
            )
    return out


SIZE_WEIGHTS = {"S": 1, "M": 2, "L": 4}


def progress(data):
    tasks = data.get("tasks", [])
    weights = [SIZE_WEIGHTS.get(t.get("size"), 0) for t in tasks]
    done_flags = [t.get("status") == "done" for t in tasks]
    return {
        "raw": (sum(done_flags), len(tasks)),
        "weighted": (
            sum(w for w, done in zip(weights, done_flags) if done),
            sum(weights),
        ),
    }


def render_markdown(data):
    lines = []
    for t in data.get("tasks", []):
        checkbox = "[x]" if t.get("status") == "done" else "[ ]"
        indent = "  " if str(t.get("id", "")).split(".")[-1] != "0" else ""
        stories = ", ".join(t.get("user_stories") or []) or "—"
        lines.append(
            f"{indent}- {checkbox} {t.get('id')} {t.get('type')}: {t.get('outcome')} "
            f"({stories}) [{t.get('size')}/{t.get('tier')}]"
        )
        cases = t.get("cases") or []
        if cases:
            lines.append(f"{indent}    Cases:")
            for case in cases:
                lines.append(f"{indent}    - {case}")
    lines.append("")
    lines.append("---")
    ordering = compute_ordering(data)
    lines.append(f"Sequence: {', '.join(ordering['sequence'])}")
    if ordering["parallel"]:
        groups = "; ".join(", ".join(group) for group in ordering["parallel"])
        lines.append(f"Parallel: {groups}")
    carried_flags = data.get("carried_flags") or []
    if carried_flags:
        lines.append("Carried flags:")
        lines.extend(f"- {flag}" for flag in carried_flags)
    decisions = data.get("decisions") or []
    if decisions:
        lines.append("Decisions:")
        lines.extend(f"- {decision}" for decision in decisions)
    return "\n".join(lines)


def render_series(data):
    lines = []
    for t in data.get("tasks", []):
        commit = t.get("commit")
        if not commit:
            continue
        artifacts = ", ".join(t.get("artifacts") or [])
        lines.append(f"{commit} · {t.get('outcome')} · {artifacts}")
    return "\n".join(lines)


def validate_schema(data):
    out = []
    ids = set()
    if "adr" not in data:
        out.append("feature: missing 'adr'")
    for t in data.get("tasks", []):
        tid = t.get("id", "?")
        if not isinstance(t.get("id"), str):
            out.append(
                f"task {tid}: id must be a quoted string — unquoted YAML numbers corrupt ('2.10' -> 2.1)"
            )
        for f in REQ_TASK - set(t):
            out.append(f"task {tid}: missing '{f}'")
        if t.get("type") not in TYPES:
            out.append(f"task {tid}: bad type {t.get('type')!r}")
        if t.get("status") not in STATUS:
            out.append(f"task {tid}: bad status")
        if t.get("size") not in SIZE:
            out.append(f"task {tid}: bad size")
        if t.get("tier") not in TIER:
            out.append(f"task {tid}: bad tier {t.get('tier')!r}")
        if tid in ids:
            out.append(f"task {tid}: duplicate id")
        else:
            ids.add(tid)
    return out
