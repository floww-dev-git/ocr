import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tasks_lib import (
    TasksError,
    check_readability,
    dump,
    load,
    progress,
    render_markdown,
    render_series,
    set_status,
    validate_all,
)  # noqa: E402


def _repo_root():
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    return result.stdout.strip()


def _run_validate(args):
    try:
        data = load(args.file)
    except TasksError as e:
        print(str(e))
        return 1
    findings = validate_all(data, _repo_root())
    warnings = check_readability(data)
    if findings:
        print("\n".join(findings))
        if warnings:
            print("\nWARN (not blocking):")
            print("\n".join(f"  {w}" for w in warnings))
        return 1
    print("OK")
    if warnings:
        print(f"\nWARN (not blocking) — {len(warnings)} readability findings:")
        print("\n".join(f"  {w}" for w in warnings))
    return 0


def _run_view(args):
    try:
        data = load(args.file)
    except TasksError as e:
        print(str(e))
        return 1
    print(render_markdown(data))
    return 0


def _run_series(args):
    try:
        data = load(args.file)
    except TasksError as e:
        print(str(e))
        return 1
    print(render_series(data))
    return 0


def _run_status(args):
    try:
        data = load(args.file)
    except TasksError as e:
        print(str(e))
        return 1
    for t in data.get("tasks", []):
        print(f"{t.get('id')} {t.get('status')}")
    return 0


def _run_progress(args):
    try:
        data = load(args.file)
    except TasksError as e:
        print(str(e))
        return 1
    result = progress(data)
    done, total = result["raw"]
    wdone, wtotal = result["weighted"]
    raw_pct = (done / total * 100) if total else 0
    weighted_pct = (wdone / wtotal * 100) if wtotal else 0
    print(f"raw: {done}/{total} ({raw_pct:.0f}%)")
    print(f"weighted: {wdone}/{wtotal} ({weighted_pct:.0f}%)")
    return 0


def _apply_status_change(path, task_id, status):
    try:
        data = load(path)
    except TasksError as e:
        print(str(e))
        return 1
    try:
        updated = set_status(data, task_id, status)
    except TasksError as e:
        print(str(e))
        return 1
    findings = validate_all(updated, _repo_root())
    if findings:
        print("\n".join(findings))
        return 1
    dump(updated, path)
    print(f"{task_id} -> {status}")
    return 0


def _run_tick(args):
    return _apply_status_change(args.file, args.id, "done")


def _run_untick(args):
    return _apply_status_change(args.file, args.id, "todo")


def _run_set_status(args):
    return _apply_status_change(args.file, args.id, args.status)


def main():
    parser = argparse.ArgumentParser(prog="tasks.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate", help="Validate a tasks YAML file"
    )
    validate_parser.add_argument("file")
    validate_parser.set_defaults(func=_run_validate)

    view_parser = subparsers.add_parser(
        "view", help="Render a readable markdown view of a tasks YAML file"
    )
    view_parser.add_argument("file")
    view_parser.set_defaults(func=_run_view)

    status_parser = subparsers.add_parser(
        "status", help="Print per-task id + status"
    )
    status_parser.add_argument("file")
    status_parser.set_defaults(func=_run_status)

    progress_parser = subparsers.add_parser(
        "progress", help="Print raw and size-weighted completion ratios"
    )
    progress_parser.add_argument("file")
    progress_parser.set_defaults(func=_run_progress)

    series_parser = subparsers.add_parser(
        "series",
        help="Print the push-gate commit series: one line per task with a non-null commit",
    )
    series_parser.add_argument("file")
    series_parser.set_defaults(func=_run_series)

    tick_parser = subparsers.add_parser(
        "tick",
        help="Set a task's status to done (fail-closed: refuses + exits 1 if revalidation fails)",
    )
    tick_parser.add_argument("file")
    tick_parser.add_argument("id")
    tick_parser.set_defaults(func=_run_tick)

    untick_parser = subparsers.add_parser(
        "untick",
        help="Set a task's status to todo (fail-closed: refuses + exits 1 if revalidation fails)",
    )
    untick_parser.add_argument("file")
    untick_parser.add_argument("id")
    untick_parser.set_defaults(func=_run_untick)

    set_status_parser = subparsers.add_parser(
        "set-status",
        help="Set a task's status explicitly (fail-closed: refuses + exits 1 if revalidation fails)",
    )
    set_status_parser.add_argument("file")
    set_status_parser.add_argument("id")
    set_status_parser.add_argument("status")
    set_status_parser.set_defaults(func=_run_set_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
