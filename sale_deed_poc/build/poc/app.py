"""FastAPI portal — upload many deeds, Analyze, watch each get read one at a time,
then see the combined chain verdict.

Routes
  GET  /                      → the single-page UI
  POST /api/upload            → store files, return a session id + file list
  GET  /api/analyze/{sid}     → Server-Sent Events: one 'deed' event per file as it is
                                read, then one 'chain' event, then 'done'
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from analyze_deed import analyze_deed
from chain import validate_chain
from extract import inventory_file, extract_one
from ingest import file_to_page_pngs, page_count, MAX_PAGES
from report import build_report


def _deed_label(n: int) -> str:
    return chr(ord('A') + n) if n < 26 else f"D{n + 1}"

BASE = Path(__file__).parent
UPLOADS = BASE / "uploads"
UPLOADS.mkdir(exist_ok=True)

app = FastAPI(title="Sale Deed Chain Validator — POC")

# session id -> list of stored file paths (in-memory; prototype only)
SESSIONS: dict[str, list[Path]] = {}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (BASE / "static" / "index.html").read_text(encoding="utf-8")


@app.post("/api/upload")
async def upload(files: list[UploadFile]) -> JSONResponse:
    sid = uuid.uuid4().hex[:12]
    sdir = UPLOADS / sid
    sdir.mkdir(parents=True, exist_ok=True)
    stored: list[Path] = []
    listing = []
    for i, f in enumerate(files):
        dest = sdir / f"{i:02d}_{Path(f.filename).name}"
        dest.write_bytes(await f.read())
        stored.append(dest)
        listing.append({"deed_id": chr(ord('A') + i), "filename": f.filename})
    SESSIONS[sid] = stored
    return JSONResponse({"session_id": sid, "files": listing})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/api/analyze/{sid}")
async def analyze(sid: str) -> StreamingResponse:
    paths = SESSIONS.get(sid)

    async def stream():
        if not paths:
            yield _sse("error", {"message": "Unknown session. Please re-upload."})
            return

        deeds = []
        gid = 0  # global deed counter across all files
        for fi, path in enumerate(paths):
            yield _sse("file_start", {"file_index": fi, "filename": path.name})
            try:
                total_pages = await run_in_threadpool(page_count, path)
                pages = await run_in_threadpool(file_to_page_pngs, path)
                last = len(pages) - 1
                if total_pages > len(pages):
                    yield _sse("warning", {
                        "file_index": fi, "filename": path.name,
                        "message": f"{path.name} has {total_pages} pages but only the first {len(pages)} were "
                                   f"processed (cap DEED_MAX_PAGES={MAX_PAGES}). Raise the cap to include the rest.",
                    })
                # persist rendered pages so the UI can show the document + provenance overlay
                page_urls = []
                for n, png in enumerate(pages):
                    fn = f"f{fi}_p{n}.png"
                    (UPLOADS / sid / fn).write_bytes(png)
                    page_urls.append(f"/pages/{sid}/{fn}")

                # --- Pass 1: inventory (what's in this file?) ---
                segments = await run_in_threadpool(inventory_file, pages)
                if not segments:  # fall back to treating the whole file as one document
                    from schema import DocSegment
                    segments = [DocSegment(doc_type="Document", page_start=0, page_end=last)]
                yield _sse("file_inventory", {
                    "file_index": fi, "filename": path.name,
                    "documents": [
                        {"doc_type": s.doc_type, "summary": s.summary, "is_title_doc": s.is_title_doc,
                         "page_label": (f"p.{s.page_start + 1}" if s.page_start == s.page_end else f"pp.{s.page_start + 1}–{s.page_end + 1}")}
                        for s in segments
                    ],
                })

                # --- Pass 2: detailed extraction per document ---
                for s in segments:
                    ps = max(0, min(s.page_start, last))
                    pe = max(ps, min(s.page_end, last))
                    did = _deed_label(gid); gid += 1
                    deed = await run_in_threadpool(extract_one, pages[ps:pe + 1], path.name)
                    deed.deed_id = did
                    deed.doc_role = "primary" if s.is_title_doc else "link"
                    flags = analyze_deed(deed)
                    deeds.append(deed)
                    yield _sse("deed", {
                        "deed_id": did, "file_index": fi, "filename": path.name,
                        "page_label": (f"p.{ps + 1}" if ps == pe else f"pp.{ps + 1}–{pe + 1}"),
                        "doc_role": deed.doc_role,
                        "deed": deed.model_dump(),     # boxes are already slice-relative
                        "flags": flags,
                        "page_images": page_urls[ps:pe + 1],
                    })
                yield _sse("file_done", {"file_index": fi, "filename": path.name, "count": len(segments)})
            except Exception as e:  # surface, don't crash the stream
                yield _sse("deed_error", {"deed_id": f"file{fi}", "filename": path.name, "message": str(e)})

        if len(deeds) < 2:
            yield _sse("chain", {
                "overall": "review",
                "overall_label": "Need at least 2 deeds",
                "overall_blurb": "Chain validation compares consecutive transfers — upload 2 or more linked deeds.",
                "counts": {}, "links": [], "findings": [],
                "property": {}, "glance": {"deeds": len(deeds)}, "ordered_deed_ids": [d.deed_id for d in deeds],
            })
        else:
            chain = await run_in_threadpool(validate_chain, deeds)
            yield _sse("chain", build_report(deeds, chain))

        yield _sse("done", {"ok": True})

    return StreamingResponse(stream(), media_type="text/event-stream")


# static assets (js/css) live under /static; rendered deed pages under /pages
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
app.mount("/pages", StaticFiles(directory=str(UPLOADS)), name="pages")
