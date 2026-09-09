#!/usr/bin/env python3
"""Orphaned-importer check — the inverse of check-dead-contracts.py.

WHY: check-dead-contracts asks "does this interface method have a consumer?".
That guards the BUILD direction. Nothing guarded the DELETE direction, and a
deletion's blast radius is the inverse of its own directory: when REF-001
dissolved the 19-fact-port design inside workflow_engine/, the engine side was
deleted but producer-side adapters and tests survived in SIX other apps,
importing interfaces that no longer existed — 42 files, 5,252 lines of dead
code, 14 test-collection errors that silently voided a directory's coverage.
It survived ~6 ADRs and many reviews because every review scope was set to
workflow_engine/. A reviewer scoped to the deleted directory structurally
CANNOT see this class of breakage; only a repo-wide query can.

Rule: when a public symbol disappears from a contract file (ports/,
storage_interfaces/, app_interfaces/, adapters/), no file anywhere in the repo
may still import it. Removal and its blast radius land in the same change.

Modes:
  Hook (PostToolUse):  no args, Edit|Write JSON on stdin — fires when a contract
                       file is edited; compares it against HEAD.
  Hook (PreToolUse):   --staged, Bash JSON on stdin — fires on `git commit`;
                       covers deletions done via `rm`, which emit no Edit event.
  CLI:                 --staged (no stdin) or <file.py> [...]
  Self-test:           --self-test

Fail-closed: an internal error blocks with an explanation rather than passing
silently. Only a genuinely absent git (impossible on the commit path) passes.
"""
import json
import os
import re
import subprocess
import sys

CONTRACT_PATH = re.compile(
    r"/(ports|storage_interfaces|app_interfaces|adapters)/[^/]+\.py$"
)
SYMBOL_DEFS = [
    re.compile(r"^class\s+([A-Za-z_]\w*)", re.M),
    re.compile(r"^def\s+([A-Za-z_]\w*)", re.M),
    re.compile(r"^([A-Z][A-Z0-9_]*)\s*(?::[^=]+)?=", re.M),
]
GREP_TIMEOUT = 60
REPO_ROOT = [None]  # set once in main(); grep results are repo-relative


class ToolingError(Exception):
    """git could not answer a question we need answered — never guess."""


def git(*args, check=True):
    try:
        result = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=GREP_TIMEOUT
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ToolingError(f"git {' '.join(args)}: {exc}") from exc
    if check and result.returncode not in (0, 1):
        raise ToolingError(f"git {' '.join(args)} exited {result.returncode}")
    return result


def public_symbols(source):
    found = set()
    for pattern in SYMBOL_DEFS:
        found.update(pattern.findall(source))
    return {name for name in found if not name.startswith("_")}


def head_source(repo_path):
    result = git("show", f"HEAD:{repo_path}", check=False)
    return result.stdout if result.returncode == 0 else None


def current_source(repo_path, repo_root):
    try:
        with open(os.path.join(repo_root, repo_path)) as handle:
            return handle.read()
    except OSError:
        return None


def dotted(repo_path):
    module = repo_path[:-3].replace("/", ".")
    return module[: -len(".__init__")] if module.endswith(".__init__") else module


def grep_literal(needle):
    """Candidate files containing a literal string.

    Literal (-F) on purpose: `git grep -E` is POSIX ERE, which has no \\s or \\b,
    so a regex written in Python syntax silently matches nothing. Gather wide
    here, then match precisely in Python where the regex dialect is ours.
    """
    result = git(
        "grep", "-l", "--untracked", "-F", "-e", needle, "--", "*.py", check=False
    )
    return {line for line in result.stdout.splitlines() if line}


def importer_files(repo_path):
    """Files that reach this module — dotted path, or `from pkg import mod`."""
    module = dotted(repo_path)
    candidates = grep_literal(module)

    if "." in module:
        package, name = module.rsplit(".", 1)
        from_import = re.compile(
            rf"from\s+{re.escape(package)}\s+import\b[^#\n]*\b{re.escape(name)}\b"
        )
        for candidate in grep_literal(package):
            source = current_source(candidate, REPO_ROOT[0] or ".")
            if source and from_import.search(source):
                candidates.add(candidate)

    candidates.discard(repo_path)
    return sorted(candidates)


def orphans_for(repo_path, removed, repo_root):
    if not removed:
        return []
    violations = []
    for importer in importer_files(repo_path):
        source = current_source(importer, repo_root)
        if source is None:
            continue
        still_used = sorted(
            name for name in removed if re.search(rf"\b{re.escape(name)}\b", source)
        )
        if still_used:
            violations.append((importer, still_used))
    return violations


def removed_symbols(repo_path, repo_root):
    before = head_source(repo_path)
    if before is None:
        return set()  # newly added file — nothing can have been removed
    after = current_source(repo_path, repo_root)
    if after is None:
        return public_symbols(before)  # file deleted — everything went with it
    return public_symbols(before) - public_symbols(after)


def report(all_violations):
    lines = ["Orphaned importers — a deleted contract is still imported elsewhere:"]
    for repo_path, violations in all_violations:
        lines.append(f"  removed from {repo_path}:")
        for importer, symbols in violations:
            lines.append(f"    {importer} still imports {', '.join(symbols)}")
    lines.append(
        "  A deletion's blast radius is the inverse of its own directory — the "
        "producers live in other apps. Delete or migrate every importer in THIS "
        "change, or restore the contract. (REF-001: 42 stranded files, 14 "
        "test-collection errors.)"
    )
    return "\n".join(lines) + "\n"


def check_paths(paths, repo_root):
    all_violations = []
    for repo_path in paths:
        if not CONTRACT_PATH.search("/" + repo_path.lstrip("/")):
            continue
        violations = orphans_for(
            repo_path, removed_symbols(repo_path, repo_root), repo_root
        )
        if violations:
            all_violations.append((repo_path, violations))
    return all_violations


def staged_contract_paths():
    result = git("diff", "--cached", "--name-status")
    paths = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2 and parts[0][:1] in {"M", "D"}:
            paths.append(parts[-1])
    return paths


def repo_root_or_raise():
    result = git("rev-parse", "--show-toplevel")
    root = result.stdout.strip()
    if not root:
        raise ToolingError("not inside a git repository")
    return root


def to_repo_relative(path, repo_root):
    absolute = os.path.abspath(path)
    return os.path.relpath(absolute, repo_root) if os.path.isabs(path) else path


def self_test():
    failures = []

    before = (
        "import abc\n"
        "class GuardFactPort(abc.ABC):\n"
        "    pass\n"
        "class KeptPort(abc.ABC):\n"
        "    pass\n"
        "class _Private:\n"
        "    pass\n"
        "MAX_FACTS = 3\n"
    )
    after = "import abc\nclass KeptPort(abc.ABC):\n    pass\n"
    removed = public_symbols(before) - public_symbols(after)
    if removed != {"GuardFactPort", "MAX_FACTS"}:
        failures.append(f"expected GuardFactPort+MAX_FACTS removed, got {removed}")
    if "_Private" in public_symbols(before):
        failures.append("private symbol leaked into public set")

    if dotted("workflow_engine/ports/guard_fact_port.py") != (
        "workflow_engine.ports.guard_fact_port"
    ):
        failures.append("dotted() mangled a module path")
    if dotted("workflow_engine/ports/__init__.py") != "workflow_engine.ports":
        failures.append("dotted() mishandled __init__.py")

    for good in (
        "workflow_engine/ports/guard_fact_port.py",
        "bps/app_interfaces/service_interface.py",
        "bps/adapters/tdr_service.py",
        "iam/storage_interfaces/user_storage_interface.py",
    ):
        if not CONTRACT_PATH.search("/" + good):
            failures.append(f"path matcher missed contract file {good}")
    for bad in ("workflow_engine/storages/foo.py", "bps/interactors/do_thing.py"):
        if CONTRACT_PATH.search("/" + bad):
            failures.append(f"path matcher wrongly matched {bad}")

    if orphans_for("x/ports/p.py", set(), "/tmp"):
        failures.append("empty removal set should short-circuit to no violations")

    if failures:
        print("SELF-TEST FAILED:\n" + "\n".join(failures))
        return 1
    print("SELF-TEST PASSED")
    return 0


def hook_paths_from_stdin(staged_mode, repo_root):
    if not sys.stdin.isatty():
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, ValueError):
            payload = {}
    else:
        payload = {}

    if staged_mode:
        command = (payload.get("tool_input") or {}).get("command")
        if command is not None and not re.search(r"^\s*git\s+commit", command):
            return None  # a Bash call that isn't a commit — not our business
        return staged_contract_paths()

    path = (payload.get("tool_input") or {}).get("file_path")
    return [to_repo_relative(path, repo_root)] if path else []


def main(argv):
    staged_mode = "--staged" in argv
    explicit = [arg for arg in argv if not arg.startswith("--")]
    try:
        repo_root = repo_root_or_raise()
        REPO_ROOT[0] = repo_root
        if explicit:
            paths = [to_repo_relative(path, repo_root) for path in explicit]
        else:
            paths = hook_paths_from_stdin(staged_mode, repo_root)
        if paths is None:
            return 0
        all_violations = check_paths(paths, repo_root)
    except ToolingError as exc:
        sys.stderr.write(
            f"check-orphaned-importers could not verify this change: {exc}\n"
            "Blocking rather than guessing — re-run once git is responsive, or "
            "confirm by hand that no other app imports the removed contract.\n"
        )
        return 2
    except Exception as exc:  # fail-closed on our own bugs
        sys.stderr.write(f"check-orphaned-importers internal error: {exc!r}\n")
        return 2

    if all_violations:
        sys.stderr.write(report(all_violations))
        return 2
    if explicit:
        print("PASS — no orphaned importers")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main(sys.argv[1:]))
