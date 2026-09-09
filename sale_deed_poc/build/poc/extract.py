"""Extract — two passes over an uploaded file.

Pass 1 (inventory_file): a fast, cheap scan that answers "what documents are in this
file, and on which pages?" — because a single upload often bundles a sale deed with its
link/parent documents.

Pass 2 (extract_one): a detailed read of ONE document (a page slice) into a DeedRecord.

The model is abstracted behind these two functions so it can be swapped. The cheap
inventory runs on Flash; the heavy extraction runs on Pro.
"""
from __future__ import annotations

import os

from google import genai
from google.genai import types

from ingest import downscale_png
from schema import DeedRecord, DocSegment, PageLabel, PageMap

MODEL = os.environ.get("DEED_MODEL", "gemini-3.1-pro-preview")              # heavy extraction
INVENTORY_MODEL = os.environ.get("INVENTORY_MODEL", "gemini-3.1-pro-preview")  # boundary detection is hard → Pro

_INVENTORY_PROMPT = """You are given the pages of ONE uploaded Indian property file, IN ORDER. A single file \
very often BUNDLES several SEPARATE registered documents — typically a main/current deed followed by its \
'link documents' (the prior/parent deeds in its chain of title), and sometimes a front summary/index sheet \
and supporting papers. Each link document is a SEPARATE registered document even though it is photocopied \
into the same file.

Your job is PAGE-BY-PAGE boundary detection. For EACH page, decide whether a NEW registered document BEGINS \
on that page. A new document typically begins with:
- a fresh non-judicial STAMP PAPER or e-stamp certificate, or a new document TITLE ('SALE DEED', \
'DEVELOPMENT AGREEMENT', 'PARTITION DEED', 'GENERAL POWER OF ATTORNEY');
- a CERTIFIED COPY of a prior/LINK deed — these are often OLD and HANDWRITTEN and begin with a header like \
"Doc No. <number>/<year>" or "Doc. No. <number> of <year>", or a two-column "Copy of Document | Copy of \
endorsements and certificates" layout, and end with "ATTESTED / SUB-REGISTRAR". START A NEW DOCUMENT at \
every such "Doc No. .../<year>" header — each certified copy is its OWN separate prior document;
- a new 'Document No.' / registration number, or a clear change of parties, year and stamp.
A front-of-file tabular 'Registration Details / Link Documents' summary sheet is its own document (doc_type \
'Registration Summary'). A long file is typically: [optional summary sheet] + [the main/current deed and its \
registration-endorsement sheets] + [several certified-copy LINK documents, each with its own Doc-No header]. \
The first content page always starts a document.

Return one entry PER PAGE with: page (0-based), starts_new_document (true/false), and — only when \
starts_new_document is true — doc_type, doc_no (if visible), and a one-line summary. When unsure whether a \
page starts a new document, prefer TRUE (over-segmenting is safer than merging two deeds)."""

_TITLE_KINDS = ("sale", "gift", "partition", "settlement", "release", "conveyance")


def _is_title(doc_type: str | None) -> bool:
    dt = (doc_type or "").lower()
    return any(k in dt for k in _TITLE_KINDS) and "agreement" not in dt

_EXTRACT_PROMPT = """These pages are ONE registered Indian property document. Read it into the response \
schema as faithfully as possible. The pages may be scanned, photographed, multilingual (English / Telugu / \
Kannada / Hindi / Marathi / Tamil), and contain handwritten endorsements.

- Identify the deed_type precisely. If it is NOT a registered sale (e.g. a GPA / Power of Attorney, an \
Agreement to Sell, a Will, a Gift, or a Partition), say so in deed_type — this matters legally.
- NAMES: always give `name` in ENGLISH (transliterate from Tamil/Telugu/etc.), and put the name exactly as \
written in the original script into `name_original`. Capture the relation marker (s/o, w/o, d/o) and the \
relative's name — these disambiguate people across deeds.
- CRUCIAL IDENTIFIERS — capture carefully when present: PAN (format like 'ABCDE1234F'), Aadhaar / any government ID \
(into `aadhaar`), survey number and plot number, document/registration number, SRO, and the registration \
and execution dates (ISO yyyy-mm-dd).
- For property, give extent exactly as written in extent_text, and ALSO normalise to square yards in \
extent_sqyd when you can (1 acre = 4840 sq yd, 1 sq m = 1.196 sq yd, 1 sq ft = 0.111 sq yd). The property \
details often sit in a 'Schedule of Property' section — read it.
- prior_deed_refs: list every prior document number cited as the seller's source of title (the recital / \
"flow of title"). Format like '1234/1998'.
- Set executed_via_gpa=true if a power-of-attorney holder signed on behalf of the owner.
- PROVENANCE: in `boxes`, for each of these key fields you find — doc_no, seller, buyer, consideration, \
survey_no, registration_date — return one entry with the field label, the value, the 0-based page index it \
appears on (relative to the pages you were given), and its bounding box as [ymin, xmin, ymax, xmax] \
normalised to 0-1000 on that page.
- confidence: your overall confidence 0..1. low_confidence_fields: name any field you are unsure about.
Do not invent values. Use null when a field is genuinely absent."""


_CLIENT: genai.Client | None = None


def _client() -> genai.Client:
    # Cache one client. Creating it per-call let Python GC it mid-request,
    # which closed the underlying httpx session ("client has been closed").
    global _CLIENT
    if _CLIENT is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to Solution4/build/poc/.env "
                "(this build is configured for real extraction — no mock)."
            )
        _CLIENT = genai.Client(api_key=key)
    return _CLIENT


def _image_parts(page_pngs: list[bytes]) -> list[types.Part]:
    return [types.Part.from_bytes(data=png, mime_type="image/png") for png in page_pngs]


def inventory_file(page_pngs: list[bytes]) -> list[DocSegment]:
    """Pass 1 — segment a (possibly bundled) file into its constituent documents via
    per-page boundary detection, then group consecutive pages into DocSegments.
    ALL pages are sent (downscaled) so no link document is ever missed."""
    n = len(page_pngs)
    parts = _image_parts([downscale_png(p) for p in page_pngs])  # low-res: boundary detection only
    parts.append(types.Part.from_text(text=_INVENTORY_PROMPT))
    resp = _client().models.generate_content(
        model=INVENTORY_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PageMap,
            temperature=0.0,
        ),
    )
    pmap: PageMap = resp.parsed
    by_page = {p.page: p for p in (pmap.pages or []) if 0 <= p.page < n}

    # collect document-start pages; always treat page 0 as a start
    starts: list[PageLabel] = []
    for i in range(n):
        pl = by_page.get(i)
        if i == 0 or (pl and pl.starts_new_document):
            starts.append(pl or PageLabel(page=i, starts_new_document=True))

    # group consecutive pages into segments
    segments: list[DocSegment] = []
    for idx, pl in enumerate(starts):
        ps = pl.page
        pe = (starts[idx + 1].page - 1) if idx + 1 < len(starts) else n - 1
        segments.append(DocSegment(
            doc_type=pl.doc_type or "Document",
            page_start=ps, page_end=max(ps, pe),
            summary=pl.summary,
            is_title_doc=_is_title(pl.doc_type),
        ))
    return segments


def extract_one(page_pngs: list[bytes], source_filename: str) -> DeedRecord:
    """Pass 2 — detailed read of ONE document (the given page slice) into a DeedRecord.
    Box page indices are relative to the slice passed in."""
    parts = _image_parts(page_pngs)
    parts.append(types.Part.from_text(text=_EXTRACT_PROMPT))
    resp = _client().models.generate_content(
        model=MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DeedRecord,
            temperature=0.0,
        ),
    )
    deed: DeedRecord = resp.parsed
    deed.source_filename = source_filename
    return deed
