import pathlib
import subprocess

import pytest
from tasks_lib import (
    TasksError,
    check_ordering,
    check_readability,
    check_tick_evidence,
    compute_ordering,
    load,
    progress,
    render_markdown,
    render_series,
    set_status,
    validate_all,
    validate_schema,
)

FIX = pathlib.Path(__file__).parent / "fixtures"
REPO = subprocess.run(
    ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
).stdout.strip()


def test_valid_fixture_passes_schema():
    assert validate_schema(load(FIX / "valid.yaml")) == []


def test_bad_enum_reported():
    findings = validate_schema(load(FIX / "bad_enum.yaml"))
    assert any("tier" in f for f in findings)


def test_missing_required_field_reported():
    findings = validate_schema(load(FIX / "bad_missing_field.yaml"))
    assert any("outcome" in f for f in findings)


def test_duplicate_id_reported():
    findings = validate_schema(load(FIX / "bad_dup_id.yaml"))
    assert any("duplicate" in f.lower() for f in findings)


def test_load_bad_json_raises():
    with pytest.raises(TasksError):
        load(FIX / "does_not_exist.yaml")


def test_done_task_with_real_artifact_passes():
    assert check_tick_evidence(load(FIX / "valid.yaml"), REPO) == []


def test_done_task_without_evidence_flagged():
    findings = check_tick_evidence(
        load(FIX / "bad_tick_no_evidence.yaml"), REPO
    )
    assert any("evidence" in f.lower() for f in findings)


def test_valid_ordering_passes():
    assert check_ordering(load(FIX / "valid.yaml")) == []


def test_cycle_flagged():
    findings = check_ordering(load(FIX / "bad_cycle.yaml"))
    assert any("cycle" in f.lower() for f in findings)


def test_unknown_dep_flagged():
    findings = check_ordering(load(FIX / "bad_forward_dep.yaml"))
    assert any("unknown" in f.lower() for f in findings)


def test_compute_parallel_groups_independent_tasks():
    result = compute_ordering(load(FIX / "valid.yaml"))
    assert isinstance(result["parallel"], list)
    assert isinstance(result["sequence"], list)
    # 2.0 and 2.1 both depend only on 1.0 — independent of each other, same layer
    parallel_ids = [frozenset(group) for group in result["parallel"]]
    assert any({"2.0", "2.1"} <= group for group in parallel_ids)


def test_done_before_dep_done_flagged():
    data = load(FIX / "valid.yaml")
    for t in data["tasks"]:
        if t["id"] == "2.2":
            t["status"] = "done"  # 2.2 depends_on 2.1, which is still todo
    findings = check_ordering(data)
    assert any("done before its dependency" in f.lower() for f in findings)


def test_render_markdown_includes_checkboxes_outcome_and_cases():
    md = render_markdown(load(FIX / "valid.yaml"))
    assert "- [x]" in md  # 1.0 is done
    assert "- [ ]" in md  # 2.0 (and others) are todo
    assert (
        "Domain exceptions have a single base class every guard/interactor can raise against."
        in md
    )
    assert "Cases:" in md


def test_progress_computes_raw_and_weighted_done_counts():
    # valid.yaml: only 1.0 (size M) is done, out of 6 tasks sized
    # M,L,S,M,S,S -> weights 2,4,1,2,1,1 = 11 total, 2 done (1.0's weight)
    result = progress(load(FIX / "valid.yaml"))
    assert result["raw"] == (1, 6)
    assert result["weighted"] == (2, 11)


def test_set_status_updates_matching_task_and_returns_a_copy():
    data = load(FIX / "valid.yaml")
    updated = set_status(data, "2.0", "done")
    assert (
        next(t["status"] for t in updated["tasks"] if t["id"] == "2.0")
        == "done"
    )
    # original data is untouched — set_status must not mutate its input
    assert (
        next(t["status"] for t in data["tasks"] if t["id"] == "2.0") == "todo"
    )


def test_set_status_unknown_id_raises():
    data = load(FIX / "valid.yaml")
    with pytest.raises(TasksError):
        set_status(data, "9.9", "done")


def test_render_series_lists_only_tasks_with_commit():
    # valid.yaml: only 1.0 carries a non-null commit ("9f2a1c7"); every other
    # task's commit is null and must be skipped.
    out = render_series(load(FIX / "valid.yaml"))
    assert out.splitlines() == [
        "9f2a1c7 · Domain exceptions have a single base class every guard/interactor can raise against. "
        "· common/exceptions/__init__.py, BaseExceptionClass"
    ]


def test_render_series_skips_tasks_with_null_commit():
    data = load(FIX / "valid.yaml")
    for t in data["tasks"]:
        if t["id"] == "2.1":
            t["commit"] = "abc1234"
    out = render_series(data)
    lines = out.splitlines()
    assert len(lines) == 2
    assert any(line.startswith("abc1234 ·") for line in lines)
    # 2.0, 2.2, 2.3, 3.0 remain null-commit and must not appear
    assert not any(
        "A guard battery evaluates every S2 gate condition" in line
        for line in lines
    )


# --- check_readability (warn-level: field budget + nickname denylist) ---------


def _task(**over):
    base = dict(
        id="1.1",
        type="task",
        status="todo",
        outcome="Move an item to the next stage",
        user_stories=["US-1"],
        depends_on=[],
        inputs=["TransitionContext"],
        output="ExecuteTransitionInteractor",
        outline="Build the interactor. See ADR §3.",
        cases=["happy path (US-1 AC1)"],
        size="S",
        tier="judgment",
        artifacts=[],
    )
    base.update(over)
    return {
        "adr": "a.md",
        "tasks": [base],
        "carried_flags": [],
        "decisions": [],
    }


def test_check_readability_clean_task_has_no_warnings():
    assert check_readability(_task()) == []


def test_check_readability_flags_over_budget_outline():
    out = check_readability(_task(outline="x" * 901))
    assert len(out) == 1 and "outline is 901 chars (budget 900)" in out[0]


def test_check_readability_allows_a_dense_judgment_outline_under_budget():
    # Re-fitted 2026-07-20: the old 300 cap flagged 91% of live tasks. A dense
    # but legitimate outline (median across REF-001 is 664) must not warn.
    assert check_readability(_task(outline="x" * 664)) == []


def test_check_readability_budget_does_not_vary_by_size():
    # `size` does not predict outline length (S median 676, L median 539), so the
    # old L-only exception gave extra room to the tasks that needed it least.
    for size in ("S", "M", "L"):
        assert check_readability(_task(size=size, outline="x" * 664)) == []
        assert len(check_readability(_task(size=size, outline="x" * 901))) == 1


def test_check_readability_flags_nickname_a_reader_cannot_look_up():
    out = check_readability(
        _task(outline="Wire the door to the walk. See ADR §3.")
    )
    assert len(out) == 2
    assert any("'the door'" in w for w in out) and any(
        "'the walk'" in w for w in out
    )


def test_check_readability_does_not_flag_lookupable_project_vocabulary():
    # 'slice', 'integration closer', 'build-once' have a defined home — not nicknames.
    assert (
        check_readability(
            _task(outline="The slice's integration closer. Build-once.")
        )
        == []
    )


def test_check_readability_flags_nickname_in_a_list_valued_inputs():
    out = check_readability(
        _task(inputs=["the door — the interactor that calls guards"])
    )
    assert any("'the door'" in w for w in out)


def test_check_readability_flags_legacy_string_inputs():
    out = check_readability(
        _task(inputs="the enum from 1.0; the DTO from 1.1")
    )
    assert len(out) == 1 and "author it as a list" in out[0]


def test_check_readability_is_not_wired_into_validate_all():
    # The flip to blocking is deliberate future work — see tasks_lib WHY comment.
    # 76 of 77 live REF-001 outlines are over budget; blocking would stall the feature.
    assert (
        validate_all(_task(outline="x" * 999, inputs="a paragraph"), ".") == []
    )


# --- signature shape: inputs/output are types, not a reading list -------------


def test_check_readability_accepts_a_clean_signature():
    assert (
        check_readability(
            _task(
                inputs=["TransitionContext", "FieldCriteriaConfig"],
                output="FieldCriteriaGuard",
            )
        )
        == []
    )


def test_check_readability_accepts_generic_type_forms():
    assert (
        check_readability(
            _task(inputs=["List[GuardResult]", "Optional[Transition]"])
        )
        == []
    )


def test_check_readability_flags_a_path_in_inputs():
    out = check_readability(
        _task(inputs=["workflow_engine/guards/field_guard.py"])
    )
    assert len(out) == 1 and "paths live in `artifacts`" in out[0]


def test_check_readability_flags_a_story_id_in_inputs():
    out = check_readability(_task(inputs=["US-3"]))
    assert len(out) == 1 and "`user_stories`" in out[0]


def test_check_readability_flags_an_adr_ref_in_inputs():
    out = check_readability(_task(inputs=["ADR-006 §D3"]))
    assert len(out) == 1 and "`adr`" in out[0]


def test_check_readability_flags_a_task_id_in_inputs():
    out = check_readability(_task(inputs=["1.2"]))
    assert len(out) == 1 and "`depends_on`" in out[0]


def test_check_readability_flags_prose_in_inputs():
    out = check_readability(
        _task(inputs=["the guard that was built in task one"])
    )
    assert len(out) == 1 and "reads as prose" in out[0]


def test_check_readability_flags_a_path_in_output():
    out = check_readability(
        _task(output="workflow_engine/guards/field_guard.py")
    )
    assert len(out) == 1 and "paths live in `artifacts`" in out[0]


def test_check_readability_flags_outcome_elaborating_after_an_em_dash():
    out = check_readability(
        _task(outcome="Slice-1 integration suite — a move blocked end-to-end")
    )
    assert len(out) == 1 and "belongs in `outline`" in out[0]


def test_check_readability_allows_an_em_dash_inside_outline():
    # outline is where the second thought is SUPPOSED to go.
    assert (
        check_readability(
            _task(outline="Read from ctx.payload — not storage. See ADR §3.")
        )
        == []
    )


def test_check_readability_flags_a_blocker_stated_in_prose():
    # Real case (relieve-v2 task 10.4): "BLOCKED IF STEP 6 HAS NOT LANDED" sat in
    # the outline of a task queued THREE positions earlier, so check_ordering saw
    # nothing and the slice closed APPROVED with an unbuildable task inside it.
    out = check_readability(
        _task(
            outline="BLOCKED IF STEP 6 HAS NOT LANDED. Sum over step 6's finder."
        )
    )
    assert len(out) == 1 and "blocker in prose" in out[0]
    assert "depends_on" in out[0]


def test_check_readability_allows_blocked_by_a_mechanism():
    # "blocked by <a hook/constraint>" describes a mechanism, not a task order —
    # the only false positive measured across the 8 relieve-v2 files.
    assert (
        check_readability(
            _task(
                outline="A third recording client is blocked by the scaffolding hook."
            )
        )
        == []
    )
