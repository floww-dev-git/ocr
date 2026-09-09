"""Run the full pipeline on a file and write a standalone HTML report.
Usage:
  uv run python run_full.py <pdf> [out.html]   # extract (slow) + cache + render
  uv run python run_full.py --cached [out.html] # re-render from cache (instant; for tuning the look)
"""
import json
import sys
from pathlib import Path

from report import build_report_v2
from report_html import render_report_v2
from schema import DeedRecord

CACHE = Path("out/deeds.json")

if sys.argv[1] == "--cached":
    OUT = sys.argv[2] if len(sys.argv) > 2 else "out/real-report.html"
    deeds = [DeedRecord(**d) for d in json.loads(CACHE.read_text(encoding="utf-8"))]
    print(f"loaded {len(deeds)} cached documents", flush=True)
else:
    from ingest import file_to_page_pngs
    from extract import inventory_file, extract_one

    PDF = sys.argv[1]
    OUT = sys.argv[2] if len(sys.argv) > 2 else "out/real-report.html"  # out/ is gitignored
    pages = file_to_page_pngs(PDF)
    print(f"pages: {len(pages)}", flush=True)
    segs = inventory_file(pages)
    print(f"documents identified: {len(segs)}", flush=True)

    deeds = []
    for i, s in enumerate(segs):
        ps, pe = s.page_start, s.page_end
        print(f"  extracting {i+1}/{len(segs)}: {s.doc_type} (pp {ps+1}-{pe+1}) ...", flush=True)
        d = extract_one(pages[ps:pe + 1], Path(PDF).name)
        d.deed_id = chr(ord('A') + i)
        deeds.append(d)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps([d.model_dump() for d in deeds], ensure_ascii=False), encoding="utf-8")

rep = build_report_v2(deeds)
Path(OUT).parent.mkdir(parents=True, exist_ok=True)
Path(OUT).write_text(render_report_v2(rep), encoding="utf-8")

print(f"\nVERDICT: {rep['verdict']['level']} — {rep['verdict']['headline']}", flush=True)
print(f"title deeds: {rep['stats']['title_deeds']} · authority: {len(rep['docs_by_role']['authority'])} · "
      f"metadata: {len(rep['docs_by_role']['metadata'])} · need-review: {rep['stats']['need_review']} · breaks: {rep['stats']['breaks']}", flush=True)
print("ROLE CLASSIFICATION:", flush=True)
for d in deeds:
    print(f"  [{d.doc_role}] {d.deed_type} {d.doc_no or ''}", flush=True)
print(f"\nwrote {OUT}", flush=True)
