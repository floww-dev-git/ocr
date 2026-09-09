#!/usr/bin/env python3
"""Divergent test-scaffolding check.

WHY: three sightings in one feature (REF-001). An `interactor` fixture copied
across 11 files (caught at S1, then AGAIN at S2), and `build_actor` defined
three times under workflow_engine/tests/ with DIFFERENT defaults
(role_identification_ids=["role_1"] in interactors/conftest.py vs [] in
enrolment_mocks.py). The nearest definition silently shadows, so a test can pass
against scaffolding the reader never saw.

testing.md already forbids this, but its clause is FIXTURE-scoped and kept
missing these: twice the duplicate was a plain helper function, not a fixture.
Prose that has failed three times on the same class needs a lower rung.

Deliberately narrow, to stay cheap and non-annoying:
  - only same-named MODULE-LEVEL defs, both under the same app's tests/ tree
  - only flagged when the two bodies DIFFER (identical copies are duplication,
    but divergence is the bug that makes a green suite lie)
  - only flagged when THIS change authored the divergence: a helper byte-identical
    to its HEAD version is pre-existing debt and is left alone. Measured on this
    repo, ~2% of 12,315 test files already carry a divergent pair; blocking an
    unrelated edit to one of them is how a good check gets disabled.

Identical copies are left to review. This hook exists for the divergence case.

Modes:
  Hook: no args, PostToolUse Edit|Write JSON on stdin
  CLI:  <file.py> [...]
  Self-test: --self-test
"""
import json
import os
import re
import subprocess
import sys

TEST_PATH = re.compile(r"(^|/)tests?/")
DEF = re.compile(r"^def\s+([A-Za-z_]\w*)\s*\(", re.M)
# Names too generic to be worth cross-file comparison.
IGNORED = {"main", "setup", "teardown"}
TIMEOUT = 30


def app_of(repo_path):
    parts = repo_path.split("/")
    return parts[0] if parts else ""


def module_level_defs(source):
    return {name for name in DEF.findall(source) if name not in IGNORED}


def body_of(source, name):
    """Source of a module-level def, whitespace-normalised."""
    pattern = re.compile(
        rf"^def\s+{re.escape(name)}\s*\(.*?(?=^\S|\Z)", re.M | re.S
    )
    match = pattern.search(source)
    if not match:
        return None
    return " ".join(match.group(0).split())


def read(path):
    try:
        with open(path) as handle:
            return handle.read()
    except OSError:
        return None


def sibling_definitions(name, app, exclude, repo_root):
    """Other test files in the same app defining a module-level `name`."""
    try:
        result = subprocess.run(
            ["git", "grep", "-l", "--untracked", "-E", "-e",
             f"^def {name}\\(", "--", f"{app}/*"],
            capture_output=True, text=True, timeout=TIMEOUT, cwd=repo_root,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []  # tooling unavailable — never false-block
    return [
        line for line in result.stdout.splitlines()
        if line and line != exclude and TEST_PATH.search("/" + line)
    ]


def head_source(repo_path, repo_root):
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{repo_path}"],
            capture_output=True, text=True, timeout=TIMEOUT, cwd=repo_root,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def check_file(repo_path, repo_root):
    source = read(os.path.join(repo_root, repo_path))
    if source is None:
        return []
    before = head_source(repo_path, repo_root)
    app = app_of(repo_path)
    findings = []
    for name in sorted(module_level_defs(source)):
        mine = body_of(source, name)
        if mine is None:
            continue
        # Pre-existing debt: this helper is untouched since HEAD, so whatever
        # divergence exists, this change did not author it. Not our business.
        if before is not None and body_of(before, name) == mine:
            continue
        for other in sibling_definitions(name, app, repo_path, repo_root):
            theirs = body_of(read(os.path.join(repo_root, other)) or "", name)
            if theirs is not None and theirs != mine:
                findings.append((name, other))
    return findings


def report(repo_path, findings):
    lines = [f"Divergent test scaffolding in {repo_path}:"]
    for name, other in findings:
        lines.append(
            f"  '{name}' is also defined — with a DIFFERENT body — in {other}"
        )
    lines.append(
        "  Same name, different behaviour. A reader (or a later agent) who finds "
        "one copy will assume it is the one in play — and in a conftest the "
        "nearest definition genuinely shadows. Hoist ONE copy to the shared "
        "conftest/common_fixtures and import it, or give this one a name that "
        "says how it differs. (testing.md, Shared Fixtures — third sighting on "
        "REF-001.)"
    )
    return "\n".join(lines) + "\n"


def self_test():
    failures = []

    a = "def build_actor(is_admin=False):\n    return Actor(roles=['role_1'])\n"
    b = "def build_actor(is_admin=False):\n    return Actor(roles=[])\n"
    if body_of(a, "build_actor") == body_of(b, "build_actor"):
        failures.append("diverging bodies compared equal")
    if body_of(a, "build_actor") != body_of(a.replace("    ", "  "), "build_actor"):
        failures.append("whitespace normalisation failed")
    if body_of(a, "missing") is not None:
        failures.append("body_of invented a missing def")

    source = "def helper():\n    pass\n\n\nclass T:\n    def method(self):\n        pass\n"
    defs = module_level_defs(source)
    if defs != {"helper"}:
        failures.append(f"expected only module-level defs, got {defs}")

    if not TEST_PATH.search("/workflow_engine/tests/interactors/conftest.py"):
        failures.append("test path matcher missed a tests/ file")
    if TEST_PATH.search("/workflow_engine/interactors/do_thing.py"):
        failures.append("test path matcher wrongly matched production code")
    if app_of("workflow_engine/tests/x.py") != "workflow_engine":
        failures.append("app_of mis-parsed")

    if failures:
        print("SELF-TEST FAILED:\n" + "\n".join(failures))
        return 1
    print("SELF-TEST PASSED")
    return 0


def repo_root():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None


def main(argv):
    root = repo_root()
    if root is None:
        return 0

    if argv:
        paths = [
            os.path.relpath(os.path.abspath(p), root) if os.path.isabs(p) else p
            for p in argv
        ]
    else:
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            return 0
        path = (payload.get("tool_input") or {}).get("file_path")
        if not path:
            return 0
        paths = [os.path.relpath(os.path.abspath(path), root)]

    exit_code = 0
    for repo_path in paths:
        if not repo_path.endswith(".py") or not TEST_PATH.search("/" + repo_path):
            continue
        findings = check_file(repo_path, root)
        if findings:
            sys.stderr.write(report(repo_path, findings))
            exit_code = 2
        elif argv:
            print(f"PASS {repo_path}")
    return exit_code


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main([a for a in sys.argv[1:] if not a.startswith("--")]))
