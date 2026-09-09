from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from document_extraction.dtos.inventory_dtos import PageBoundaryDTO


class PageLabel(BaseModel):
    """Per-page boundary signal used to segment a bundled file into documents."""

    page: int = Field(description="0-based page index")
    starts_new_document: bool = Field(
        description="True if a NEW registered document begins on this page"
    )
    doc_type: Optional[str] = Field(
        default=None,
        description=(
            "Document type if this page starts one, e.g. 'Sale Deed', "
            "'Partition Deed', 'GPA', 'Registration Summary'"
        ),
    )
    doc_no: Optional[str] = Field(
        default=None, description="Document/registration number if visible"
    )
    summary: Optional[str] = Field(
        default=None,
        description="One-line description if this page starts a document",
    )


class PageMap(BaseModel):
    """Per-page classification of one uploaded file, in page order."""

    pages: List[PageLabel] = Field(default_factory=list)


# Carried verbatim from sale_deed_poc/build/poc/extract.py::_INVENTORY_PROMPT. The
# certified-copy paragraph is the part that earns its keep: a photocopied prior deed
# has no fresh stamp paper, so only its "Doc No. .../<year>" header marks the join.
INVENTORY_PROMPT = """You are given the pages of ONE uploaded Indian property file, IN ORDER. A single file \
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


def read_page_boundaries(page_map: PageMap) -> Tuple[PageBoundaryDTO, ...]:
    """The model's answer, dropped into plain DTOs before any grouping sees it."""
    return tuple(
        PageBoundaryDTO(
            page=page_label.page,
            starts_new_document=page_label.starts_new_document,
            doc_type=page_label.doc_type,
            doc_no=page_label.doc_no,
            summary=page_label.summary,
        )
        for page_label in (page_map.pages or [])
    )
