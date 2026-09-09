#!/usr/bin/env python3
"""Import-smoke test a list of production python modules.

Sets up Django, then imports each given file's dotted module path and
records any exception raised at import time. Does not run pytest -- this
is a fast import-level check only.

Usage:
    DJANGO_SETTINGS_MODULE=sales_crm_backend.settings.local \
        python .claude/scripts/import-smoke.py <path-to-file-list.txt>

    # or pass file paths directly as argv:
    python .claude/scripts/import-smoke.py bps/workflows/foo.py bps/models/bar.py
"""
import os
import sys
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ImportResult:
    module_name: str
    file_path: str
    ok: bool
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None


def file_path_to_module_name(file_path: str) -> str:
    without_ext = (
        file_path[: -len(".py")] if file_path.endswith(".py") else file_path
    )
    if without_ext.endswith("/__init__"):
        without_ext = without_ext[: -len("/__init__")]
    return without_ext.replace("/", ".")


def read_file_paths(argv: List[str]) -> List[str]:
    if len(argv) == 1:
        raise SystemExit(
            "usage: import-smoke.py <file-list.txt | file1.py file2.py ...>"
        )
    if len(argv) == 2 and os.path.isfile(argv[1]) and argv[1].endswith(".txt"):
        with open(argv[1]) as f:
            return [line.strip() for line in f if line.strip()]
    return argv[1:]


def setup_django() -> None:
    # Running this file directly puts its own directory on sys.path[0], not
    # the repo root -- add the CWD (expected to be the repo root) so the
    # project's top-level packages (sales_crm_backend, bps, ...) resolve.
    repo_root = os.getcwd()
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "sales_crm_backend.settings.local"
    )
    import django

    django.setup()


def import_modules(file_paths: List[str]) -> List[ImportResult]:
    import importlib

    results: List[ImportResult] = []
    for file_path in file_paths:
        module_name = file_path_to_module_name(file_path)
        try:
            importlib.import_module(module_name)
        except (
            Exception
        ) as exc:  # noqa: BLE001 -- deliberately broad, this is a smoke test
            results.append(
                ImportResult(
                    module_name=module_name,
                    file_path=file_path,
                    ok=False,
                    exception_type=type(exc).__name__,
                    exception_message=str(exc),
                )
            )
        else:
            results.append(
                ImportResult(
                    module_name=module_name, file_path=file_path, ok=True
                )
            )
    return results


def print_summary(results: List[ImportResult]) -> int:
    failures = [r for r in results if not r.ok]
    print(
        f"Scanned: {len(results)}  Clean: {len(results) - len(failures)}  Failed: {len(failures)}"
    )
    if failures:
        print("\nFailures:")
        for r in failures:
            print(
                f"  {r.file_path}  ->  {r.exception_type}: {r.exception_message}"
            )
    return 1 if failures else 0


def main() -> int:
    file_paths = read_file_paths(sys.argv)
    setup_django()
    results = import_modules(file_paths)
    return print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
