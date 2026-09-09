#!/usr/bin/env python3
"""PostToolUse validator for feature tasks YAML files (tasks-ADR-*.yaml).

WHY: the tasks YAML is the single source of truth for a plan's dependency
order, schema, and tick-evidence — a malformed or corrupted write (bad
enum, dependency cycle, a done task with no artifact evidence) should be
caught the moment it's written, not discovered later at tick time.

Rule: on every Edit/Write to a file matching `tasks-ADR-*.yaml`, load it and
run tasks_lib.validate_all(). Any finding blocks the write (exit 2). The
schema reference doc (tasks-schema.yaml) and test fixtures deliberately do
NOT match this pattern — they carry no `tasks:` list and would fail
validation despite being correct as-is.

Modes:
  Hook:       no args — PostToolUse JSON on stdin, skips non-matching files,
              exit 2 + stderr on violation
  Self-test:  python3 check-tasks-yaml.py --self-test
"""
import importlib.util
import json
import os
import re
import subprocess
import sys

# PyYAML availability guard — tasks_lib needs PyYAML, and this is the first
# PostToolUse hook with a third-party dependency. If the interpreter the harness
# picked lacks it, re-exec with the repo venv python; if that's unavailable too,
# fail OPEN (skip validation) rather than crash and block a legitimate edit.
if importlib.util.find_spec("yaml") is None:
    _venv_py = os.path.join(
        os.environ.get("CLAUDE_PROJECT_DIR", ""), "venv", "bin", "python"
    )
    if os.path.exists(_venv_py) and os.path.realpath(
        _venv_py
    ) != os.path.realpath(sys.executable):
        try:
            os.execv(
                _venv_py, [_venv_py, os.path.abspath(__file__), *sys.argv[1:]]
            )
        except OSError:
            pass  # exec failed (e.g. not executable) — fall through to fail-open, never crash
    sys.stderr.write(
        "check-tasks-yaml: PyYAML unavailable — skipping tasks validation for this write.\n"
    )
    sys.exit(0)

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"),
)

from tasks_lib import (
    TasksError,
    check_readability,
    load,
    validate_all,
)  # noqa: E402

TASKS_FILE = re.compile(r"^tasks-ADR-.*\.yaml$")


def is_tasks_file(path):
    return bool(path) and bool(TASKS_FILE.match(os.path.basename(path)))


def _repo_root():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()


def _base_dir():
    base_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if base_dir:
        return base_dir
    return _repo_root()


def run_hook():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    path = (payload.get("tool_input") or {}).get("file_path")
    if not is_tasks_file(path):
        return 0
    base_dir = _base_dir()
    if not base_dir:
        sys.stderr.write(
            "check-tasks-yaml: could not resolve a repo root (CLAUDE_PROJECT_DIR unset and "
            "git rev-parse failed) — skipping validation for this write.\n"
        )
        return 0
    try:
        data = load(path)
    except TasksError as e:
        sys.stderr.write(f"Tasks YAML error in {path}:\n  {e}\n")
        return 2
    findings = validate_all(data, base_dir)
    if findings:
        sys.stderr.write(
            f"Tasks YAML validation failed for {path}:\n"
            + "\n".join(f"  {f}" for f in findings)
            + "\n"
        )
        return 2
    warnings = check_readability(data)
    if warnings:
        sys.stderr.write(
            f"Tasks YAML readability warnings for {path} (not blocking):\n"
            + "\n".join(f"  {w}" for w in warnings)
            + "\n"
        )
    return 0


def self_test():
    fixtures_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "scripts",
        "tests",
        "fixtures",
    )
    base_dir = _base_dir()
    failures = []

    valid_data = load(os.path.join(fixtures_dir, "valid.yaml"))
    valid_findings = validate_all(valid_data, base_dir)
    if valid_findings:
        failures.append(f"valid.yaml: expected clean, got {valid_findings}")

    bad_data = load(os.path.join(fixtures_dir, "bad_enum.yaml"))
    bad_findings = validate_all(bad_data, base_dir)
    if not bad_findings:
        failures.append("bad_enum.yaml: expected findings, got none")

    if not is_tasks_file("tasks-schema.yaml"):
        pass
    else:
        failures.append(
            "path filter: tasks-schema.yaml must NOT match tasks-ADR-*.yaml"
        )

    if failures:
        print("SELF-TEST FAILED:\n" + "\n".join(failures))
        return 1
    print("self-test OK")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        sys.exit(self_test())
    sys.exit(run_hook())
