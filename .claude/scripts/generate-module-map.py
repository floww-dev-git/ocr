#!/usr/bin/env python3
"""Generate the module map — a one-glance index of every app/module CLAUDE.md.

WHY THIS EXISTS
The intake flow's "cheap scan" (requirement-phase station 1, beat 1) needs a
one-glance module index: module -> one-line capability -> category, so the
manager can propose candidate modules WITHOUT reading 27 CLAUDE.md files.

The map is a GENERATED VIEW of the app CLAUDE.mds. The single source of truth
stays in each app's own CLAUDE.md — hand-editing the map is drift. Regenerate:

    python3 .claude/scripts/generate-module-map.py

Stdlib-only, idempotent. Discovers CLAUDE.md files, extracts a one-line
capability from each, categorizes root apps per the project CLAUDE.md table,
nests subfolder cards under their root app, and flags AI-readiness gaps
(INSTALLED_APPS local apps that have no CLAUDE.md yet).
"""

import datetime
import os
import re
import sys

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
OUTPUT_PATH = os.path.join(
    REPO_ROOT, ".claude", "rules", "references", "module-map.md"
)
SETTINGS_DIR = os.path.join(REPO_ROOT, "sales_crm_backend", "settings")

EXCLUDED_DIR_NAMES = {".claude", "venv", "node_modules", "__pycache__", ".git"}

# Category table — mirrors the "Django Apps" table in the project CLAUDE.md.
CATEGORY_ORDER = [
    "Core",
    "Business",
    "Integration",
    "API",
    "Supporting",
    "Infrastructure",
    "Other",
]
APP_CATEGORY = {
    "sales_crm_core": "Core",
    "iam": "Core",
    "asynq": "Core",
    "bps": "Business",
    "automation_workflows": "Business",
    "fee_engine": "Business",
    "payments_engine": "Business",
    "plugins": "Integration",
    "portals": "Integration",
    "analytics_copilot": "Integration",
    "sales_crm_graphql": "API",
    "ext_client_graphql": "API",
    "floww_cli_graphql": "API",
    "engine_variables": "Supporting",
    "ib_templates": "Supporting",
    "crm_scoring": "Supporting",
    "scrutiny_report": "Supporting",
    "jobs_engine": "Infrastructure",
}

MAX_SUMMARY_LEN = 140


def find_claude_md_files():
    """Return sorted list of CLAUDE.md paths relative to REPO_ROOT (depth 1 and deeper)."""
    found = []
    for dirpath, dirnames, filenames in os.walk(REPO_ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIR_NAMES]
        if "CLAUDE.md" in filenames:
            rel = os.path.relpath(
                os.path.join(dirpath, "CLAUDE.md"), REPO_ROOT
            )
            if (
                rel == "CLAUDE.md"
            ):  # repo-root project CLAUDE.md — not a module card
                continue
            found.append(rel)
    return sorted(found)


def strip_markdown(text):
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]*)\*", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text.strip()


def extract_capability(md_path):
    """First substantive prose line: skip heading, blanks, code fences, tables, bullets."""
    abs_path = os.path.join(REPO_ROOT, md_path)
    in_code_fence = False
    with open(abs_path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line.startswith("```"):
                in_code_fence = not in_code_fence
                continue
            if in_code_fence or not line:
                continue
            if line.startswith("#"):
                continue
            if line.startswith("|") or line.startswith(">"):
                continue
            if line.startswith(("- ", "* ", "+ ")):
                continue
            summary = strip_markdown(line)
            if len(summary) < 15:  # too short to be a real capability sentence
                continue
            if len(summary) > MAX_SUMMARY_LEN:
                summary = summary[: MAX_SUMMARY_LEN - 1].rstrip() + "…"
            return summary
    return None  # nothing substantive found — junky opening line


def discover_installed_local_apps():
    """Parse the local-app list from the settings module that declares it.

    The project registers local apps in an `APPS = [...]` list (loaded into
    INSTALLED_APPS). Scan settings/*.py for that list; fall back to INSTALLED_APPS.
    """
    if not os.path.isdir(SETTINGS_DIR):
        return [], None
    for name in sorted(os.listdir(SETTINGS_DIR)):
        if not name.endswith(".py"):
            continue
        path = os.path.join(SETTINGS_DIR, name)
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        match = re.search(
            r"^APPS\s*=\s*\[(.*?)\]", content, re.MULTILINE | re.DOTALL
        )
        if match:
            apps = re.findall(r"[\"']([\w.]+)[\"']", match.group(1))
            return sorted(set(apps) | _apps_on_disk()), os.path.relpath(
                path, REPO_ROOT
            )
    return sorted(_apps_on_disk()), None


def _apps_on_disk():
    """Top-level dirs shaped like Django apps (apps.py, or models+migrations dirs) —
    catches apps built but not yet registered in settings (pre-registration code,
    e.g. a strangler-fig app mid-build, evades the APPS list)."""
    found = set()
    for name in os.listdir(REPO_ROOT):
        base = os.path.join(REPO_ROOT, name)
        if os.path.isfile(os.path.join(base, "apps.py")) or (
            os.path.isdir(os.path.join(base, "models"))
            and os.path.isdir(os.path.join(base, "migrations"))
        ):
            found.add(name)
    return found


def find_coverage_gaps(local_apps, root_apps_with_card):
    """Local apps that exist as top-level dirs but have no root CLAUDE.md."""
    gaps = []
    for app in local_apps:
        app_dir = os.path.join(REPO_ROOT, app)
        if os.path.isdir(app_dir) and app not in root_apps_with_card:
            gaps.append(app)
    return sorted(set(gaps))


def build_tree(md_files):
    """Map root app -> {'summary': str|None, 'subs': [(path, summary|None), ...]}."""
    tree = {}
    junky = []
    for rel in md_files:
        module_dir = os.path.dirname(rel)
        summary = extract_capability(rel)
        if summary is None:
            junky.append(rel)
        root = module_dir.split(os.sep)[0]
        node = tree.setdefault(root, {"summary": None, "subs": []})
        if module_dir == root:
            node["summary"] = summary
        else:
            node["subs"].append((module_dir, summary))
    for node in tree.values():
        node["subs"].sort(key=lambda item: item[0])
    return tree, junky


def render(tree, gaps, settings_source, gen_date, include_subs=False):
    lines = []
    lines.append("<!-- GENERATED FILE — DO NOT EDIT BY HAND. -->")
    lines.append(
        "<!-- Regenerate: python3 .claude/scripts/generate-module-map.py "
        "— source of truth is each app's own CLAUDE.md. -->"
    )
    lines.append("")
    lines.append("# Module Map")
    lines.append("")
    lines.append(
        "One-glance index of every app/module capability. Feeds the intake flow's "
        '"cheap scan" (requirement-phase station 1, beat 1) so the manager can propose '
        "candidate modules WITHOUT reading every CLAUDE.md."
    )
    lines.append("")
    lines.append(
        "This is a GENERATED VIEW of the app CLAUDE.mds — the single source of truth stays "
        "in each app. Hand-editing this file is drift; regenerate instead:"
    )
    lines.append("")
    lines.append("```bash")
    lines.append("python3 .claude/scripts/generate-module-map.py")
    lines.append("```")
    lines.append("")
    if include_subs:
        lines.append(
            f"_Generated {gen_date}. Sub-modules are prefixed `↳` under their app._"
        )
    else:
        lines.append(
            f"_Generated {gen_date}. App granularity only — the cheap scan proposes candidate "
            f"APPS; sub-module detail lives in each app's own CLAUDE.md (read at beat 3) and in "
            f"Phase 2's impact map. Full view: `--with-submodules`._"
        )
    lines.append("")

    by_category = {cat: [] for cat in CATEGORY_ORDER}
    for root in sorted(tree):
        by_category[APP_CATEGORY.get(root, "Other")].append(root)

    for category in CATEGORY_ORDER:
        roots = by_category[category]
        if not roots:
            continue
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| module | capability |")
        lines.append("|---|---|")
        for root in roots:
            node = tree[root]
            lines.append(
                f"| `{root}` | {node['summary'] or '_(no summary — see gaps)_'} |"
            )
            if include_subs:
                for sub_path, sub_summary in node["subs"]:
                    lines.append(
                        f"| ↳ `{sub_path}` | {sub_summary or '_(no summary)_'} |"
                    )
        lines.append("")

    lines.append("## No capability card yet")
    lines.append("")
    if gaps:
        source_note = f" (from `{settings_source}`)" if settings_source else ""
        lines.append(
            f"Local apps registered in INSTALLED_APPS{source_note} with no CLAUDE.md — "
            "AI-readiness debt:"
        )
        lines.append("")
        for app in gaps:
            lines.append(f"- `{app}`")
    else:
        lines.append("_None — every registered local app has a CLAUDE.md._")
    lines.append("")
    return "\n".join(lines)


def main():
    include_subs = "--with-submodules" in sys.argv
    md_files = find_claude_md_files()
    tree, junky = build_tree(md_files)
    root_apps_with_card = set(tree)
    local_apps, settings_source = discover_installed_local_apps()
    gaps = find_coverage_gaps(local_apps, root_apps_with_card)
    gen_date = datetime.date.today().isoformat()

    output = render(
        tree, gaps, settings_source, gen_date, include_subs=include_subs
    )
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(output + "\n")

    root_count = len(root_apps_with_card)
    sub_count = sum(len(node["subs"]) for node in tree.values())
    print(f"Wrote {os.path.relpath(OUTPUT_PATH, REPO_ROOT)}")
    print(f"  {root_count} apps, {sub_count} sub-modules, {len(gaps)} gaps")
    if gaps:
        print(f"  gaps: {', '.join(gaps)}")
    if junky:
        print(f"  {len(junky)} CLAUDE.md with no summarizable first line:")
        for rel in junky:
            print(f"    - {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
