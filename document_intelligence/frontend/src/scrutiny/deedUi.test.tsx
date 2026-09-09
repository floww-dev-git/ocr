import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  ChainOfTitle,
  DeedRecord,
  DocumentState,
  LinkVerdict,
  OwnershipReport,
  Party,
} from "@/api/contracts";
import { buildDocument, buildOwnershipReport } from "@/test/factories";
import { DeedRecordPanel } from "./DeedRecordPanel";
import { DocumentCard } from "./DocumentCard";
import { OwnershipReportView } from "./OwnershipReportView";

const NO_ACTIONS = {
  onEditField: () => {},
  onConfirmFields: () => {},
  onResolveCheck: () => {},
  onRetryVerification: () => {},
};

function deedRecord(overrides: Partial<DeedRecord> = {}): DeedRecord {
  return {
    docNo: "5820/2019",
    sro: "SRO Serilingampally",
    registrationDate: "2019-02-18",
    executionDate: "2019-02-11",
    deedType: "Sale Deed",
    sellers: [
      {
        name: "Sunita Sharma",
        nameOriginal: null,
        relation: "w/o",
        relativeName: "Anil Sharma",
        address: null,
        pan: null,
        aadhaar: null,
      },
    ],
    buyers: [
      {
        name: "Prakash Iyer",
        nameOriginal: null,
        relation: null,
        relativeName: null,
        address: null,
        pan: null,
        aadhaar: null,
      },
    ],
    property: {
      surveyNo: "142/2",
      plotNo: "17",
      extentText: "400 Sq. Yards",
      extentSqYard: 400,
      boundaries: null,
      locality: "Kondapur",
      ulpin: null,
    },
    considerationText: "Rs. 96,00,000/-",
    considerationInr: 9_600_000,
    stampDutyText: null,
    estampNo: null,
    priorDeedRefs: ["2451/2011"],
    executedViaGpa: false,
    ...overrides,
  };
}

describe("the deed record panel", () => {
  it("shows the vendor and purchaser the deed transfers between", () => {
    render(<DeedRecordPanel deedRecord={deedRecord()} />);

    expect(screen.getByText("Sunita Sharma")).toBeInTheDocument();
    expect(screen.getByText("Prakash Iyer")).toBeInTheDocument();
  });

  it("shows the relation that tells two people of the same name apart", () => {
    render(<DeedRecordPanel deedRecord={deedRecord()} />);

    expect(screen.getByText(/w\/o Anil Sharma/)).toBeInTheDocument();
  });

  it("names the prior deed the title traces through", () => {
    render(<DeedRecordPanel deedRecord={deedRecord()} />);

    expect(screen.getByText("2451/2011")).toBeInTheDocument();
  });

  it("says plainly when a deed is the root of the chain", () => {
    render(<DeedRecordPanel deedRecord={deedRecord({ priorDeedRefs: [] })} />);

    expect(screen.getByText(/root of the chain/i)).toBeInTheDocument();
  });

  it("says which party stood alone and which had others beside them", () => {
    const record = deedRecord({
      sellers: [
        deedRecord().sellers[0],
        {
          name: "Ravi Sharma",
          nameOriginal: null,
          relation: null,
          relativeName: null,
          address: null,
          pan: null,
          aadhaar: null,
        },
      ],
    });
    render(<DeedRecordPanel deedRecord={record} />);

    expect(screen.getByText(/and 1 other/i)).toBeInTheDocument();
  });
});

describe("a deed document card", () => {
  it("shows the pages it occupies inside a bundle", () => {
    const document = buildDocument({
      documentId: "deed_2",
      filename: "01_clean_chain.pdf",
      documentTypeId: "sale_deed",
      documentTypeLabel: "Sale deed",
      parentDocumentId: "bundle",
      pageStart: 4,
      pageEnd: 5,
      deedRecord: deedRecord(),
    });

    render(<DocumentCard document={document} busy={false} {...NO_ACTIONS} />);

    const card = screen.getByRole("article", { name: "01_clean_chain.pdf" });
    expect(card).toHaveTextContent("pp. 5–6");
  });

  it("shows the deed record beneath a deed", () => {
    const document = buildDocument({
      documentId: "deed_2",
      filename: "sale_deed.pdf",
      documentTypeId: "sale_deed",
      documentTypeLabel: "Sale deed",
      deedRecord: deedRecord(),
    });

    render(<DocumentCard document={document} busy={false} {...NO_ACTIONS} />);

    const card = screen.getByRole("article", { name: "sale_deed.pdf" });
    expect(within(card).getByText("Prakash Iyer")).toBeInTheDocument();
  });

  it("shows no deed record on a document that is not a deed", () => {
    const document = buildDocument({ filename: "pan_card.jpg" });

    render(<DocumentCard document={document} busy={false} {...NO_ACTIONS} />);

    expect(screen.queryByText(/root of the chain/i)).not.toBeInTheDocument();
  });
});

describe("the ownership report", () => {
  it("leads with the chain verdict headline and its plain reading", () => {
    render(
      <OwnershipReportView
        documentsById={{}}
        report={buildOwnershipReport({
          verdict: {
            level: "clean",
            headline: "Title traces cleanly from 2003 to today",
            plain: "Ownership flows through 3 registered deeds with no breaks.",
          },
        })}
      />,
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent("Title traces cleanly from 2003 to today");
    expect(region).toHaveTextContent(/no breaks/i);
  });

  it("shows the risk score without letting it stand in for the verdict", () => {
    render(
      <OwnershipReportView
        documentsById={{}}
        report={buildOwnershipReport({
          verdict: {
            level: "broken",
            headline: "The title chain is broken",
            plain: "A hand-off does not connect.",
          },
          risk: {
            score: 64,
            level: "High",
            signals: [
              {
                severity: "high",
                code: "broken_chain",
                title: "Broken ownership link",
                detail: "No continuity.",
              },
            ],
          },
        })}
      />,
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent(/Risk High/);
    expect(region).toHaveTextContent("64");
    // The verdict is its own line; risk sits beside it, not in place of it.
    expect(region).toHaveTextContent("The title chain is broken");
  });

  it("lists what the officer has to chase, worst first", () => {
    render(
      <OwnershipReportView
        documentsById={{}}
        report={buildOwnershipReport({
          attention: [
            {
              severity: "high",
              verb: "RESOLVE",
              title: "Broken link — no continuity (2451/2011 → 5820/2019)",
              detail: "The 2019 vendor was never a buyer in this chain.",
              action: "Obtain a legal title opinion.",
            },
          ],
        })}
      />,
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent("RESOLVE");
    expect(region).toHaveTextContent(/never a buyer/i);
    expect(region).toHaveTextContent(/legal title opinion/i);
  });

  it("states who owns the land now, above the history", () => {
    renderReport(timelineFixture([{ docNo: "1188/2003" }], []), {
      journey: [
        {
          kind: "owner",
          role: "Owner since 2019",
          badge: "TITLE OWNER",
          party: {
            name: "Prakash Iyer",
            nameOriginal: null,
            relative: null,
            othersCount: 0,
          },
          meta: "acquired from Sunita Sharma",
          isCurrent: true,
          verdict: null,
          label: null,
          reference: null,
          note: null,
          identityScore: null,
        },
      ],
    });

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent("TITLE OWNER");
    expect(region).toHaveTextContent("Prakash Iyer");
    expect(region).toHaveTextContent(/acquired from Sunita Sharma/);
  });

  it("numbers the deeds oldest first, the order title travelled in", () => {
    renderReport(
      timelineFixture(
        [
          { docNo: "1188/2003", registrationDate: "2003-06-12" },
          { docNo: "2451/2011", registrationDate: "2011-09-05" },
          { docNo: "5820/2019", registrationDate: "2019-02-18" },
        ],
        [{ verdict: "linked" }, { verdict: "linked" }],
      ),
    );

    const timeline = screen.getByRole("list", { name: /ownership timeline/i });
    const rows = within(timeline).getAllByRole("listitem");
    expect(rows).toHaveLength(3);
    // Oldest deed carries ordinal 1 and the earliest registration number.
    expect(rows[0]).toHaveTextContent("1");
    expect(rows[0]).toHaveTextContent("1188/2003");
    expect(rows[2]).toHaveTextContent("3");
    expect(rows[2]).toHaveTextContent("5820/2019");
  });

  it("says so when a hand-over carried ownership across", () => {
    renderReport(
      timelineFixture(
        [{ docNo: "1188/2003" }, { docNo: "2451/2011" }],
        [{ verdict: "linked", identityScore: 100 }],
      ),
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent("ownership carries over");
    expect(region).toHaveTextContent("100/100");
  });

  it("calls an approximate name match a weak link and shows its caveat", () => {
    renderReport(
      timelineFixture(
        [{ docNo: "1188/2003" }, { docNo: "2451/2011" }],
        [
          {
            verdict: "weak",
            identityScore: 80,
            notes: ["Approximate name match — verify this is the same person."],
          },
        ],
      ),
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent("weak link");
    expect(region).toHaveTextContent("80/100");
    expect(region).toHaveTextContent(/verify this is the same person/i);
  });

  it("states a gap in the space where the hand-over should have been", () => {
    renderReport(
      timelineFixture(
        [{ docNo: "2451/2011" }, { docNo: "5820/2019" }],
        [
          {
            verdict: "gap",
            notes: ["Conveys 600 sq.yd but the seller acquired only 400 sq.yd."],
          },
        ],
      ),
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent("A deed may be missing here");
    expect(region).toHaveTextContent(/only 400 sq.yd/);
  });

  it("says the chain breaks where it breaks", () => {
    renderReport(
      timelineFixture(
        [{ docNo: "2451/2011" }, { docNo: "5820/2019" }],
        [{ verdict: "broken" }],
      ),
    );

    expect(
      screen.getByRole("region", { name: /chain of title/i }),
    ).toHaveTextContent("Chain breaks here");
  });

  it("leaves a hand-over that held without a rupture heading", () => {
    renderReport(
      timelineFixture(
        [{ docNo: "1188/2003" }, { docNo: "2451/2011" }],
        [{ verdict: "linked" }],
      ),
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).not.toHaveTextContent(/may be missing here|breaks here/i);
  });

  it("still explains a rupture the engine graded without a note of its own", () => {
    renderReport(
      timelineFixture(
        [{ docNo: "2451/2011" }, { docNo: "5820/2019" }],
        [{ verdict: "gap", notes: [] }],
      ),
    );

    expect(
      screen.getByRole("region", { name: /chain of title/i }),
    ).toHaveTextContent("Ownership does not carry over between these deeds.");
  });

  it("shows a break by naming the two people who should have been one", () => {
    renderReport(
      timelineFixture(
        [
          {
            docNo: "2451/2011",
            buyers: [party("Sunita Sharma")],
          },
          {
            docNo: "5820/2019",
            sellers: [party("Mohammed Farooq")],
          },
        ],
        [{ verdict: "broken", identityScore: 12 }],
      ),
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent("Buyer in 2451/2011:");
    expect(region).toHaveTextContent("Sunita Sharma");
    expect(region).toHaveTextContent("Seller in 5820/2019:");
    expect(region).toHaveTextContent("Mohammed Farooq");
    expect(region).toHaveTextContent(
      "These should be the same person — they do not match.",
    );
  });

  it("names the deeds a break falls between, before any of them are read", () => {
    renderReport(
      timelineFixture(
        [{ docNo: "1188/2003" }, { docNo: "2451/2011" }, { docNo: "5820/2019" }],
        [{ verdict: "linked" }, { verdict: "gap" }],
      ),
    );

    expect(
      screen.getByRole("region", { name: /chain of title/i }),
    ).toHaveTextContent("Deed missing between Deed 2 and Deed 3");
  });

  it("colours the join by whether ownership carried over", () => {
    const { container } = renderReport(
      timelineFixture(
        [{ docNo: "1188/2003" }, { docNo: "2451/2011" }, { docNo: "5820/2019" }],
        [{ verdict: "linked" }, { verdict: "weak" }],
      ),
    );

    expect(container.querySelector('[data-testid="join-rail-pass"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="join-rail-warn"]')).not.toBeNull();
  });

  it("keeps a differently spelled name visible rather than dropping it", () => {
    renderReport(
      timelineFixture(
        [
          {
            docNo: "2451/2011",
            buyers: [{ ...party("Lakshmi Narayanan"), nameOriginal: "Laxmi Narayan" }],
          },
        ],
        [],
      ),
    );

    const timeline = screen.getByRole("list", { name: /ownership timeline/i });
    expect(timeline).toHaveTextContent("Lakshmi Narayanan (Laxmi Narayan)");
  });

  it("counts the parties it did not have room to name", () => {
    renderReport(
      timelineFixture(
        [
          {
            docNo: "1188/2003",
            sellers: [
              party("Govind Rao"),
              party("Ramesh Kumar"),
              party("Sunita Sharma"),
            ],
          },
        ],
        [],
      ),
    );

    const timeline = screen.getByRole("list", { name: /ownership timeline/i });
    expect(timeline).toHaveTextContent("Govind Rao, Ramesh Kumar");
    expect(timeline).toHaveTextContent(/& 1 more/);
  });

  it("lays the transactions out as a ledger, in date order", () => {
    renderReport(
      timelineFixture(
        [
          { docNo: "1188/2003", registrationDate: "2003-06-12" },
          { docNo: "2451/2011", registrationDate: "2011-09-05" },
          { docNo: "5820/2019", registrationDate: "2019-02-18" },
        ],
        [{ verdict: "linked" }, { verdict: "gap" }],
      ),
    );

    const table = screen.getByRole("table");
    const rows = within(table).getAllByRole("row");
    // One header row plus one row per deed.
    expect(rows).toHaveLength(4);
    // The first deed was handed over by nothing; it begins the chain.
    expect(rows[1]).toHaveTextContent("origin");
    expect(rows[1]).toHaveTextContent("2003-06-12");
    expect(rows[2]).toHaveTextContent("ownership carries over");
    expect(rows[3]).toHaveTextContent("gap");
    expect(table).toHaveTextContent("Sy. 142/2 Plot 17");
    expect(table).toHaveTextContent("Rs. 96,00,000/-");
  });

  it("reports what the engine found, graded", () => {
    const fixture = timelineFixture(
      [{ docNo: "2451/2011" }, { docNo: "5820/2019" }],
      [{ verdict: "gap" }],
    );
    renderReport({
      ...fixture,
      chain: {
        ...fixture.chain,
        findings: [
          {
            severity: "high",
            verdict: "gap",
            title: "Suspected missing deed",
            detail: "1 transfer conveys more extent than acquired.",
          },
        ],
      },
    });

    const findings = screen.getByRole("list", { name: /findings/i });
    expect(findings).toHaveTextContent("HIGH");
    expect(findings).toHaveTextContent("Suspected missing deed");
    expect(findings).toHaveTextContent(/more extent than acquired/);
  });

  it("shows only the questions a hand-over could actually be asked", () => {
    renderReport(
      timelineFixture(
        [{ docNo: "2451/2011" }, { docNo: "5820/2019" }],
        [
          {
            verdict: "gap",
            // `recital` and `dates` were never asked of this link.
            checks: { identity: true, property: true, extent: false },
          },
        ],
      ),
    );

    const checked = screen.getByRole("list", { name: /what was checked/i });
    expect(within(checked).getByText(/Seller is the previous buyer/)).toBeInTheDocument();
    expect(within(checked).getByText(/Extent within what was acquired/)).toBeInTheDocument();
    expect(within(checked).queryByText(/Recites the prior deed/)).toBeNull();
    expect(within(checked).queryByText(/Dates run in order/)).toBeNull();
  });

  it("counts the deeds and the span it traced", () => {
    render(
      <OwnershipReportView
        documentsById={{}}
        report={buildOwnershipReport({
          stats: {
            titleDeedCount: 3,
            spanFrom: "2003",
            spanTo: "2019",
            needReview: 1,
            breaks: 0,
          },
        })}
      />,
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent(/Title deeds\s*3/);
    expect(region).toHaveTextContent("2003 → 2019");
    expect(region).toHaveTextContent(/Need checking\s*1/);
  });

  it("separates the deeds that convey title from the ones that only look as if they do", () => {
    render(
      <OwnershipReportView
        documentsById={{}}
        report={buildOwnershipReport({
          documentsByRole: {
            title: [
              {
                documentId: "document_1",
                deedType: "Sale Deed",
                docNo: "1188/2003",
                date: "2003-06-12",
                isRoot: true,
              },
            ],
            authority: [
              {
                documentId: "document_2",
                deedType: "General Power of Attorney",
                docNo: "77/2020",
                date: "2020-01-09",
                isRoot: false,
              },
            ],
          },
        })}
      />,
    );

    expect(
      within(screen.getByRole("list", { name: /title chain/i })).getByText("1188/2003"),
    ).toBeInTheDocument();
    const authority = screen.getByRole("list", { name: /authority and supporting/i });
    expect(within(authority).getByText("77/2020")).toBeInTheDocument();
    expect(
      screen.getByRole("region", { name: /chain of title/i }),
    ).toHaveTextContent(/do NOT convey title/);
  });

  it("warns in words when the current instrument only carries authority", () => {
    render(
      <OwnershipReportView
        documentsById={{}}
        report={buildOwnershipReport({
          authority: [
            {
              documentId: "document_2",
              deedType: "Development Agreement",
              docNo: "77/2020",
              owner: "Sunita Sharma",
              holder: "Prakash Iyer",
            },
          ],
          documentsByRole: {
            authority: [
              {
                documentId: "document_2",
                deedType: "Development Agreement",
                docNo: "77/2020",
                date: "2020-01-09",
                isRoot: false,
              },
            ],
          },
        })}
      />,
    );

    const region = screen.getByRole("region", { name: /chain of title/i });
    expect(region).toHaveTextContent(/does not transfer ownership/i);
    expect(region).toHaveTextContent("Sunita Sharma");
  });
});

function party(name: string): Party {
  return {
    name,
    nameOriginal: null,
    relation: null,
    relativeName: null,
    address: null,
    pan: null,
    aadhaar: null,
  };
}

interface LinkSpec {
  verdict: LinkVerdict;
  identityScore?: number;
  notes?: string[];
  checks?: Partial<Record<string, boolean>>;
}

interface TimelineFixture {
  chain: ChainOfTitle;
  documentsById: Record<string, DocumentState>;
}

/**
 * A chain and the reads it is traced against. The timeline joins one to the other,
 * so a test has to supply both: `chain.orderedDocumentIds` names the deeds and
 * their order, `documentsById` carries what was read off each.
 *
 * `links[k]` is the hand-over from deed k to deed k+1, matching how the engine
 * emits them.
 */
function timelineFixture(
  deeds: Partial<DeedRecord>[],
  links: LinkSpec[],
): TimelineFixture {
  const documentIds = deeds.map((_, index) => `document_${index + 1}`);
  const documentsById: Record<string, DocumentState> = {};
  deeds.forEach((overrides, index) => {
    documentsById[documentIds[index]] = buildDocument({
      documentId: documentIds[index],
      deedRecord: deedRecord(overrides),
    });
  });
  return {
    documentsById,
    chain: {
      overall: "review",
      counts: {},
      orderedDocumentIds: documentIds,
      excludedDocumentIds: [],
      duplicateDocumentIds: [],
      rolesByDocumentId: {},
      links: links.map((link, index) => ({
        fromDocumentId: documentIds[index],
        toDocumentId: documentIds[index + 1],
        fromDocNo: deeds[index].docNo ?? null,
        toDocNo: deeds[index + 1].docNo ?? null,
        verdict: link.verdict,
        identityScore: link.identityScore ?? 100,
        checks: link.checks ?? { identity: true, property: true },
        notes: link.notes ?? [],
      })),
      findings: [],
    },
  };
}

function renderReport(
  fixture: TimelineFixture,
  reportOverrides: Partial<OwnershipReport> = {},
) {
  return render(
    <OwnershipReportView
      documentsById={fixture.documentsById}
      report={buildOwnershipReport({ chain: fixture.chain, ...reportOverrides })}
    />,
  );
}
