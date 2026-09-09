import pathlib
import shutil
import subprocess
import sys

from tasks_lib import dump, load

CLI = pathlib.Path(__file__).parents[1] / "tasks.py"
FIX = pathlib.Path(__file__).parent / "fixtures"


def run(*a):
    return subprocess.run(
        [sys.executable, str(CLI), *a], capture_output=True, text=True
    )


def test_validate_ok():
    r = run("validate", str(FIX / "valid.yaml"))
    assert r.returncode == 0
    assert "OK" in r.stdout


def test_validate_bad():
    r = run("validate", str(FIX / "bad_enum.yaml"))
    assert r.returncode == 1
    assert "tier" in r.stdout


def test_status_prints_per_task_id_and_status():
    r = run("status", str(FIX / "valid.yaml"))
    assert r.returncode == 0
    assert "1.0 done" in r.stdout
    assert "2.0 todo" in r.stdout
    assert "3.0 in_progress" in r.stdout


def test_progress_prints_raw_and_weighted_ratios_with_percent():
    r = run("progress", str(FIX / "valid.yaml"))
    assert r.returncode == 0
    assert "1/6" in r.stdout
    assert "2/11" in r.stdout
    assert "%" in r.stdout


def test_tick_valid_task_succeeds(tmp_path):
    # 2.1 depends only on 1.0 (done); give it a real, resolvable artifact so
    # tick-evidence passes — valid.yaml's todo tasks otherwise carry no artifacts.
    f = tmp_path / "t.yaml"
    data = load(FIX / "valid.yaml")
    for t in data["tasks"]:
        if t["id"] == "2.1":
            t["artifacts"] = ["common/exceptions/__init__.py"]
    dump(data, f)

    r = run("tick", str(f), "2.1")

    assert r.returncode == 0
    reloaded = load(f)
    assert (
        next(t["status"] for t in reloaded["tasks"] if t["id"] == "2.1")
        == "done"
    )


def test_tick_fails_closed_on_missing_evidence_and_leaves_file_unchanged(
    tmp_path,
):
    # 2.1 has empty artifacts in the unmodified fixture — ticking it to done
    # cannot resolve any evidence, so the refusal must fire and the file must
    # be byte-identical afterwards.
    f = tmp_path / "t.yaml"
    shutil.copy(FIX / "valid.yaml", f)
    before = f.read_bytes()

    r = run("tick", str(f), "2.1")

    assert r.returncode == 1
    assert f.read_bytes() == before


def test_tick_unknown_id_fails(tmp_path):
    f = tmp_path / "t.yaml"
    shutil.copy(FIX / "valid.yaml", f)
    before = f.read_bytes()

    r = run("tick", str(f), "9.9")

    assert r.returncode == 1
    assert f.read_bytes() == before


def test_untick_valid_task_succeeds(tmp_path):
    # 1.0 is done with real artifacts and no dependents are done, so
    # unticking it back to todo revalidates clean.
    f = tmp_path / "t.yaml"
    shutil.copy(FIX / "valid.yaml", f)

    r = run("untick", str(f), "1.0")

    assert r.returncode == 0
    reloaded = load(f)
    assert (
        next(t["status"] for t in reloaded["tasks"] if t["id"] == "1.0")
        == "todo"
    )


def test_set_status_to_in_progress_succeeds(tmp_path):
    f = tmp_path / "t.yaml"
    shutil.copy(FIX / "valid.yaml", f)

    r = run("set-status", str(f), "2.1", "in_progress")

    assert r.returncode == 0
    reloaded = load(f)
    assert (
        next(t["status"] for t in reloaded["tasks"] if t["id"] == "2.1")
        == "in_progress"
    )


def test_set_status_invalid_status_value_fails_closed_and_leaves_file_unchanged(
    tmp_path,
):
    f = tmp_path / "t.yaml"
    shutil.copy(FIX / "valid.yaml", f)
    before = f.read_bytes()

    r = run("set-status", str(f), "2.1", "bogus_status")

    assert r.returncode == 1
    assert f.read_bytes() == before


def test_series_lists_only_tasks_with_a_commit(tmp_path):
    # 1.0 already carries commit "9f2a1c7" in the fixture; give 2.1 a commit
    # too and confirm both surface while the remaining null-commit tasks don't.
    f = tmp_path / "t.yaml"
    data = load(FIX / "valid.yaml")
    for t in data["tasks"]:
        if t["id"] == "2.1":
            t["commit"] = "abc1234"
    dump(data, f)

    r = run("series", str(f))

    assert r.returncode == 0
    assert "9f2a1c7" in r.stdout
    assert "abc1234" in r.stdout
    assert (
        "GuardFactProvider defines the one contract every S2 guard reads transition facts through."
        in r.stdout
    )
    # 2.0 stays null-commit and must not appear
    assert "A guard battery evaluates every S2 gate condition" not in r.stdout
