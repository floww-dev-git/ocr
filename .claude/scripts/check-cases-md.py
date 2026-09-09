#!/usr/bin/env python3
"""Check every gateway-test `cases.md` against the grouped-case contract.

    python3 .claude/scripts/check-cases-md.py                 # whole repo
    python3 .claude/scripts/check-cases-md.py fee_engine      # one app or suite

Format home: `.claude/skills/gateway-tests-expert/references/cases-md-format.md`.
What it enforces, per file:

  * every case id is `<Letter><n>` — no bare numbers, no mnemonic prefixes
  * each group is ONE contiguous run, numbered from 1
  * a `**Groups:**` legend exists and names exactly the letters the table uses, in order
  * the count line carries `N cases, G groups` and both numbers are true
  * no prose still cites a case by a bare number ("see case 7") — a renumber rots those
    silently, so they must read "see case C2"
  * every `builder_json` cell names a file in the suite's `factory_jsons/`, and — only in a
    file claiming `all covered` — every `Test` link resolves

A file is written BEFORE its tests exist, so a dangling `Test` link is normal while a suite is
being built. It is only a fault once the file claims the suite is covered; until then the
dangling links are reported as notes and do not fail the run.

Exit 1 on any finding, so it can gate a commit or ride a hook.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CASE_ID = re.compile(r"^[A-Z]\d+$")
COUNT_LINE = re.compile(r"\*\*(\d+)\s+cases?,\s*(\d+)\s+groups?,\s*([^*]*)\*\*")
GROUPS_LINE = re.compile(r"\*\*Groups:\*\*\s*(.+?)(?=\n\s*\n|\Z)", re.S)
NUMERIC_REFERENCE = re.compile(r"\b[Cc]ases?\s+\d+\b")
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
SUITE_GLOBS = ("*/tests/gateway_tests/*/cases.md", "*/*/tests/gateway_tests/*/cases.md")


def split_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def read_table(lines):
    header = next((i for i, l in enumerate(lines)
                   if l.startswith("|") and split_row(l)[0].lower() == "case"), None)
    if header is None:
        return None, []
    body = []
    for line in lines[header + 2:]:
        if not line.startswith("|"):
            break
        body.append(split_row(line))
    return header, body


def check_ids(ids):
    """Ids are grouped, each group one contiguous run numbered from 1."""
    problems, order, seen, previous = [], [], {}, None
    ungrouped = [i for i in ids if not CASE_ID.match(i)]
    if ungrouped:
        problems.append(f"case ids are not grouped: {ungrouped[:6]}"
                        f"{' …' if len(ungrouped) > 6 else ''}")
    for case_id in ids:
        if not CASE_ID.match(case_id):
            continue
        letter, number = case_id[0], int(case_id[1:])
        if letter != previous:
            if letter in seen:
                problems.append(f"group {letter} is split — a group must be one run of rows")
            order.append(letter)
            seen[letter] = 0
            previous = letter
        seen[letter] += 1
        if number != seen[letter]:
            problems.append(f"{case_id} breaks its group's numbering (expected {letter}{seen[letter]})")
    return problems, order


def check(path):
    text = path.read_text()
    header, body = read_table(text.split("\n"))
    if header is None:
        return ["no case table"], []

    problems, order = check_ids([row[0] for row in body])

    legend = GROUPS_LINE.search(text)
    if not legend:
        problems.append("no **Groups:** legend in the intro")
    else:
        flattened = " ".join(legend.group(1).split())        # the legend may wrap
        declared = [part.split(" · ")[0].strip() for part in flattened.split(" — ")]
        if declared != order:
            problems.append(f"legend names {declared}, the table uses {order}")

    count = COUNT_LINE.search(text)
    claims_full_coverage = False
    if not count:
        problems.append("count line is not the `**N cases, G groups, …**` form")
    else:
        claims_full_coverage = "all covered" in count.group(3).lower()
        if int(count.group(1)) != len(body):
            problems.append(f"count line says {count.group(1)} cases, the table has {len(body)}")
        if int(count.group(2)) != len(order):
            problems.append(f"count line says {count.group(2)} groups, the table has {len(order)}")

    stale = sorted(set(NUMERIC_REFERENCE.findall(text)))
    if stale:
        problems.append(f"prose cites cases by bare number: {stale[:5]} — use the grouped id")

    columns = [cell.lower() for cell in split_row(text.split("\n")[header])]
    unwritten = []
    for row in body:
        for name in re.findall(r"`([^`]+)`", row[columns.index("builder_json")]):
            if not (path.parent / "factory_jsons" / name).exists():
                problems.append(f"{row[0]}: builder_json names a missing fixture — {name}")
        for _label, target in LINK.findall(row[columns.index("test")]):
            if not (path.parent / target).exists():
                unwritten.append(f"{row[0]} → {target}")
    if unwritten and claims_full_coverage:
        problems.extend(f"{entry}: Test links a file that does not exist, "
                        f"but the count line claims all covered" for entry in unwritten)
    return problems, unwritten if not claims_full_coverage else []


def main():
    fragment = sys.argv[1] if len(sys.argv) > 1 else ""
    files = sorted({path for pattern in SUITE_GLOBS for path in REPO.glob(pattern)
                    if fragment in str(path) and "venv" not in path.parts})
    failed, pending = 0, 0
    for path in files:
        problems, unwritten = check(path)
        if problems:
            failed += 1
        if problems or unwritten:
            print(f"\n{path.relative_to(REPO)}")
        for problem in problems:
            print(f"   - {problem}")
        if unwritten:
            pending += 1
            print(f"   note: {len(unwritten)} test file(s) not written yet "
                  f"(the count line says so) — {unwritten[0].split(' → ')[1]} …")
    print(f"\n{len(files) - failed}/{len(files)} cases.md files clean"
          + (f", {pending} still being built" if pending else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
