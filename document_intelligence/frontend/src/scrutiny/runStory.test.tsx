import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DeedRecord, DocumentState, Party } from "@/api/contracts";
import { ApiError } from "@/api/apiError";
import { scrutinyApi } from "@/api/scrutinyApi";
import {
  buildApplication,
  buildCheck,
  buildDocument,
  buildSummary,
  MISMATCH_APPLICATION_ID,
} from "@/test/factories";
import {
  chainFrame,
  DONE_FRAME,
  docFrame,
  errorFrame,
  stepFrame,
  stubEventStream,
  summaryFrame,
} from "@/test/fakeStream";
import { buildOwnershipReport } from "@/test/factories";
import { takeUpApplication } from "@/test/takeUpApplication";
import { WorkspaceShell } from "./WorkspaceShell";

const THREAD_ID = "thread_abc";
const DOCUMENT_ID = "document_1";
const MISREAD_NAME = "MOHAMMED IRFAN SIDDIQI";
const CORRECTED_NAME = "MOHAMMED IRFAN SIDDIQUI";

const NAME_CHECK_ID = `${DOCUMENT_ID}:name`;
const ISSUER_CHECK_ID = `${DOCUMENT_ID}:issuer`;

function nameWarning() {
  return buildCheck({
    checkId: NAME_CHECK_ID,
    status: "warn",
    title: "Name matches application",
    detail: `PAN reads ${MISREAD_NAME}. Application reads Mohammed Irfan Siddiqui. Similarity 96%.`,
  });
}

function issuerWarning() {
  return buildCheck({
    checkId: ISSUER_CHECK_ID,
    group: "external",
    status: "warn",
    title: "Income Tax PAN verification did not fully match",
    detail:
      "The department holds this PAN but its record does not agree on the name.",
    fieldKey: null,
    issuerCall: {
      issuerServiceId: "itd_pan",
      name: "Income Tax PAN verification",
      endpoint: "POST /pan/verify",
      latencyMs: 912,
      requestPayload: { pan: "BNMPS7720K", name: MISREAD_NAME },
      responsePayload: { status: "VALID", nameMatch: false },
    },
  });
}

/** The document as the analyze run leaves it for the seeded mismatch. */
function readDocument(overrides: Partial<DocumentState> = {}): DocumentState {
  return buildDocument({
    documentId: DOCUMENT_ID,
    documentTypeLabel: "PAN",
    status: "attention",
    fieldValues: [
      { key: "name", value: MISREAD_NAME, confidence: 0.95, edited: false, confirmed: false },
      { key: "pan", value: "BNMPS7720K", confidence: 0.99, edited: false, confirmed: false },
    ],
    structureFindings: { photo: true, signature: true, hologram: true },
    checks: [nameWarning(), issuerWarning()],
    ...overrides,
  });
}

const QUEUED_DOCUMENT = buildDocument({
  documentId: DOCUMENT_ID,
  documentTypeId: null,
  documentTypeLabel: "",
  typeConfidence: 0,
  stage: "queued",
  status: "checking",
  pageCount: 0,
});

async function openThreadWithDocument() {
  vi.spyOn(scrutinyApi, "getApplications").mockResolvedValue([buildApplication()]);
  vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
    threadId: THREAD_ID,
    applicationId: MISMATCH_APPLICATION_ID,
    serviceOverrides: {},
    documents: [],
  });
  vi.spyOn(scrutinyApi, "addDocuments").mockResolvedValue([QUEUED_DOCUMENT]);

  render(<WorkspaceShell />);
  await takeUpApplication(MISMATCH_APPLICATION_ID);
  await userEvent.upload(
    screen.getByLabelText(/documents to attach/i),
    new File(["x"], "pan_card.jpg", { type: "image/jpeg" }),
  );
  // Staged, not uploaded: it sits on the tray until the officer presses Verify.
  await screen.findByRole("list", { name: /documents ready to verify/i });
}

async function runAnalysis() {
  stubEventStream([
    stepFrame("identify", "running"),
    docFrame(readDocument({ stage: "identifying", checks: [] })),
    stepFrame("identify", "done"),
    stepFrame("extract", "running"),
    stepFrame("extract", "done"),
    stepFrame("checks", "running"),
    stepFrame("checks", "done", 8),
    stepFrame("verify", "running"),
    docFrame(readDocument()),
    stepFrame("verify", "done"),
    summaryFrame(
      buildSummary({
        threadStatus: "attention",
        statusCounts: { pass: 7, warn: 2 },
        openItems: [
          {
            documentId: DOCUMENT_ID,
            checkId: NAME_CHECK_ID,
            text: "PAN: Name matches application",
          },
          {
            documentId: DOCUMENT_ID,
            checkId: ISSUER_CHECK_ID,
            text: "PAN: Income Tax PAN verification did not fully match",
          },
        ],
      }),
    ),
    DONE_FRAME,
  ]);
  await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));
  await waitFor(() =>
    expect(screen.getByText(/finished reading/i)).toBeInTheDocument(),
  );
  await screen.findByRole("article", { name: "pan_card.jpg" });
}

describe("the run story, driven through a real SSE body", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("walks the four steps and says what each one did", async () => {
    await openThreadWithDocument();
    await runAnalysis();

    const activity = screen.getByRole("region", { name: /analysis progress/i });
    expect(activity).toHaveTextContent(/identified the document/i);
    expect(activity).toHaveTextContent(/read the details/i);
    expect(activity).toHaveTextContent(/compared against the application/i);
    expect(activity).toHaveTextContent(/asked the issuing department/i);
    expect(activity).toHaveTextContent(/8 checks/);
  });

  it("shows the thread needs attention once the run settles", async () => {
    await openThreadWithDocument();
    await runAnalysis();

    expect(screen.getByRole("banner")).toHaveTextContent(/needs a look/i);
  });

  it("tallies the checks in the details panel", async () => {
    await openThreadWithDocument();
    await runAnalysis();

    const sidebar = screen.getByRole("complementary", {
      name: /application details/i,
    });
    // The prototype's four counts, rather than a grid of thread stats.
    expect(sidebar).toHaveTextContent("passed");
    expect(sidebar).toHaveTextContent("warnings");
    expect(sidebar).toHaveTextContent("failed");
    expect(sidebar).toHaveTextContent("to note");
    // Two of this run's checks want a look.
    expect(within(sidebar).getByText("2")).toBeInTheDocument();
  });

  it("shows what the machine read, and how sure it was", async () => {
    await openThreadWithDocument();
    await runAnalysis();

    const card = screen.getByRole("article", { name: "pan_card.jpg" });
    expect(card).toHaveTextContent(MISREAD_NAME);
  });

  it("lets the officer correct a misread value and shows the check settling", async () => {
    await openThreadWithDocument();
    await runAnalysis();
    const editField = vi.spyOn(scrutinyApi, "updateField").mockResolvedValue({
      document: readDocument({
        status: "attention",
        fieldValues: [
          { key: "name", value: CORRECTED_NAME, confidence: 0.95, edited: true, confirmed: false },
          { key: "pan", value: "BNMPS7720K", confidence: 0.99, edited: false, confirmed: false },
        ],
        checks: [
          buildCheck({ checkId: NAME_CHECK_ID, status: "pass" }),
          issuerWarning(),
        ],
      }),
      summary: buildSummary({
        threadStatus: "attention",
        statusCounts: { pass: 8, warn: 1 },
        openItems: [
          {
            documentId: DOCUMENT_ID,
            checkId: ISSUER_CHECK_ID,
            text: "PAN: Income Tax PAN verification did not fully match",
          },
        ],
      }),
      changedCheckIds: [NAME_CHECK_ID],
    });

    await userEvent.click(screen.getByRole("button", { name: /correct name/i }));
    const input = screen.getByRole("textbox", { name: /name value/i });
    await userEvent.clear(input);
    await userEvent.type(input, CORRECTED_NAME);
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(editField).toHaveBeenCalledWith({
        threadId: THREAD_ID,
        documentId: DOCUMENT_ID,
        fieldKey: "name",
        value: CORRECTED_NAME,
      }),
    );
    const card = await screen.findByRole("article", { name: "pan_card.jpg" });
    expect(card).toHaveTextContent(CORRECTED_NAME);
    expect(card).toHaveTextContent(/corrected/i);
  });

  it("keeps the thread in attention while the department still disagrees", async () => {
    await openThreadWithDocument();
    await runAnalysis();
    vi.spyOn(scrutinyApi, "updateField").mockResolvedValue({
      document: readDocument({
        checks: [buildCheck({ checkId: NAME_CHECK_ID, status: "pass" }), issuerWarning()],
      }),
      summary: buildSummary({
        threadStatus: "attention",
        openItems: [
          {
            documentId: DOCUMENT_ID,
            checkId: ISSUER_CHECK_ID,
            text: "PAN: Income Tax PAN verification did not fully match",
          },
        ],
      }),
      changedCheckIds: [NAME_CHECK_ID],
    });

    await userEvent.click(screen.getByRole("button", { name: /correct name/i }));
    await userEvent.click(screen.getByRole("button", { name: "Save" }));

    // Nothing was typed, so the row closes without a call; the point is the
    // officer's correction never claims the department changed its mind.
    expect(screen.getByRole("banner")).toHaveTextContent(/needs a look/i);
  });

  it("clears the thread only once the officer signs off the department's answer", async () => {
    await openThreadWithDocument();
    await runAnalysis();
    const resolve = vi.spyOn(scrutinyApi, "resolveCheck").mockResolvedValue({
      check: { ...issuerWarning(), manual: true },
      document: readDocument({
        status: "verified",
        checks: [nameWarning(), { ...issuerWarning(), manual: true }],
      }),
      summary: buildSummary({ threadStatus: "clear", openItems: [] }),
    });

    await userEvent.click(screen.getByRole("tab", { name: /checks/i }));
    const checks = screen.getByRole("tabpanel");
    await userEvent.click(
      within(checks).getAllByRole("button", { name: /verified by hand/i })[1],
    );

    await waitFor(() =>
      expect(resolve).toHaveBeenCalledWith({
        threadId: THREAD_ID,
        checkId: ISSUER_CHECK_ID,
        action: "manual",
      }),
    );
    expect(screen.getByRole("banner")).toHaveTextContent(/clear/i);
  });

  it("keeps showing the department's own verdict after the officer overrides it", async () => {
    await openThreadWithDocument();
    await runAnalysis();
    vi.spyOn(scrutinyApi, "resolveCheck").mockResolvedValue({
      check: { ...issuerWarning(), manual: true },
      document: readDocument({
        status: "verified",
        checks: [nameWarning(), { ...issuerWarning(), manual: true }],
      }),
      summary: buildSummary({ threadStatus: "clear", openItems: [] }),
    });

    await userEvent.click(screen.getByRole("tab", { name: /checks/i }));
    await userEvent.click(
      within(screen.getByRole("tabpanel")).getAllByRole("button", {
        name: /verified by hand/i,
      })[1],
    );

    // The audit trail: the machine still says it did not fully match, and the
    // officer's override is shown as a separate fact beside it.
    const panel = await screen.findByRole("tabpanel");
    expect(panel).toHaveTextContent(/did not fully match/i);
    expect(panel).toHaveTextContent(/needs a look/i);
    expect(panel).toHaveTextContent(/verified by hand/i);
  });

  it("discloses exactly what was asked of the department", async () => {
    await openThreadWithDocument();
    await runAnalysis();

    await userEvent.click(screen.getByRole("tab", { name: /checks/i }));
    await userEvent.click(
      screen.getByRole("button", { name: /view request and response/i }),
    );

    const panel = screen.getByRole("tabpanel");
    expect(panel).toHaveTextContent("POST /pan/verify");
    // The meta row states how long the department took, in seconds.
    expect(panel).toHaveTextContent("0.9 s");
    expect(panel).toHaveTextContent("BNMPS7720K");
    expect(panel).toHaveTextContent("nameMatch");
  });

  it("tells the officer plainly when the department already agreed", async () => {
    await openThreadWithDocument();
    await runAnalysis();
    vi.spyOn(scrutinyApi, "retryVerification").mockRejectedValue(
      new ApiError({ status: 400, errorCode: "CHECK_NOT_RETRYABLE" }),
    );

    await userEvent.click(screen.getByRole("tab", { name: /checks/i }));
    await userEvent.click(
      screen.getByRole("button", { name: /ask the department again/i }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /already agreed on this one/i,
    );
  });

  it("tells the officer to wait rather than losing an edit mid-run", async () => {
    await openThreadWithDocument();
    await runAnalysis();
    vi.spyOn(scrutinyApi, "confirmFields").mockRejectedValue(
      new ApiError({ status: 409, errorCode: "DOCUMENT_BUSY" }),
    );

    await userEvent.click(
      screen.getByRole("button", { name: /these values are right/i }),
    );

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /still being read/i,
    );
  });

  it("keeps a document that failed to read alongside the ones that worked", async () => {
    await openThreadWithDocument();
    stubEventStream([
      stepFrame("identify", "running"),
      docFrame(readDocument()),
      errorFrame("broken.pdf could not be read."),
      summaryFrame(buildSummary({ threadStatus: "attention" })),
      DONE_FRAME,
    ]);

    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));

    const activity = await screen.findByRole("region", { name: /analysis progress/i });
    await waitFor(() =>
      expect(activity).toHaveTextContent(/broken\.pdf could not be read/i),
    );
    expect(screen.getByRole("article", { name: "pan_card.jpg" })).toBeInTheDocument();
  });

  it("stops claiming work is in progress if the stream dies mid-run", async () => {
    await openThreadWithDocument();
    stubEventStream([stepFrame("identify", "running")]);

    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));

    await waitFor(() =>
      expect(screen.getByText(/finished reading/i)).toBeInTheDocument(),
    );
  });

  it("appends the note at the bottom, leaving an earlier one in place", async () => {
    await openThreadWithDocument();
    await runAnalysis();
    const getNote = vi
      .spyOn(scrutinyApi, "getNote")
      .mockResolvedValueOnce({
        threadId: THREAD_ID,
        text: "Scrutiny note for BN/2026/0377\nRecommendation: Raise shortfall",
      })
      .mockResolvedValueOnce({
        threadId: THREAD_ID,
        text: "Scrutiny note for BN/2026/0377\nRecommendation: Fit to proceed",
      });
    vi.spyOn(scrutinyApi, "resolveCheck").mockResolvedValue({
      check: { ...issuerWarning(), manual: true },
      document: readDocument({
        checks: [nameWarning(), { ...issuerWarning(), manual: true }],
      }),
      summary: buildSummary({ threadStatus: "clear", openItems: [] }),
    });

    await userEvent.click(
      screen.getByRole("button", { name: /write scrutiny note/i }),
    );
    expect(await screen.findByText(/Raise shortfall/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: /checks/i }));
    await userEvent.click(
      within(screen.getByRole("tabpanel")).getAllByRole("button", {
        name: /verified by hand/i,
      })[1],
    );
    await userEvent.click(
      screen.getByRole("button", { name: /write scrutiny note/i }),
    );

    // Both notes are on the record, in the order they were written. Replacing the
    // first would hide that a recommendation changed, and why.
    await waitFor(() => expect(getNote).toHaveBeenCalledTimes(2));
    const notes = screen.getAllByRole("region", { name: /scrutiny note/i });
    expect(notes).toHaveLength(2);
    expect(notes[0]).toHaveTextContent(/Raise shortfall/);
    expect(notes[1]).toHaveTextContent(/Fit to proceed/);
  });

  it("puts a second run below the first, never above it", async () => {
    await openThreadWithDocument();
    await runAnalysis();

    // A second document attached and verified after the first run finished.
    const second = readDocument({
      documentId: "document_2",
      filename: "pan_card_two.jpg",
      checks: [],
    });
    vi.spyOn(scrutinyApi, "addDocuments").mockResolvedValue([
      buildDocument({ documentId: "document_2", filename: "pan_card_two.jpg", stage: "queued" }),
    ]);
    stubEventStream([
      stepFrame("identify", "running"),
      docFrame(second),
      stepFrame("identify", "done"),
      summaryFrame(buildSummary({ threadStatus: "attention" })),
      DONE_FRAME,
    ]);
    await userEvent.upload(
      screen.getByLabelText(/documents to attach/i),
      new File(["x"], "pan_card_two.jpg", { type: "image/jpeg" }),
    );
    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));
    await screen.findByRole("article", { name: "pan_card_two.jpg" });

    const record = screen.getByRole("region", { name: /scrutiny record/i });
    const order = [...record.querySelectorAll("article[aria-label], section[aria-label]")]
      .map((element) => element.getAttribute("aria-label"))
      .filter((label): label is string => label !== null);

    // The first run's activity and card come before the second run's.
    expect(order.indexOf("pan_card.jpg")).toBeLessThan(
      order.indexOf("pan_card_two.jpg"),
    );
    const activities = order.filter((label) => label === "Analysis progress");
    expect(activities).toHaveLength(2);
    expect(order.indexOf("Analysis progress")).toBeLessThan(
      order.indexOf("pan_card.jpg"),
    );
  });

  it("keeps each run's progress with its own document", async () => {
    await openThreadWithDocument();
    await runAnalysis();
    vi.spyOn(scrutinyApi, "addDocuments").mockResolvedValue([
      buildDocument({ documentId: "document_2", filename: "two.jpg", stage: "queued" }),
    ]);
    stubEventStream([
      stepFrame("identify", "running"),
      docFrame(readDocument({ documentId: "document_2", filename: "two.jpg", checks: [] })),
      stepFrame("identify", "done"),
      summaryFrame(buildSummary()),
      DONE_FRAME,
    ]);
    await userEvent.upload(
      screen.getByLabelText(/documents to attach/i),
      new File(["x"], "two.jpg", { type: "image/jpeg" }),
    );
    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));
    await screen.findByRole("article", { name: "two.jpg" });

    // The second run only did `identify`; the first did all four. Each block
    // reports its own work rather than a single shared progress panel.
    const activities = screen.getAllByRole("region", { name: /analysis progress/i });
    expect(activities[0]).toHaveTextContent(/asked the issuing department/i);
    expect(activities[1]).not.toHaveTextContent(/asked the issuing department/i);
  });

  it("records what the officer submitted, above what was made of it", async () => {
    await openThreadWithDocument();
    await runAnalysis();

    const record = screen.getByRole("region", { name: /scrutiny record/i });
    expect(record).toHaveTextContent(/verify this against the application/i);
    expect(record).toHaveTextContent("pan_card.jpg");
  });

  it("nests a bundle's deeds beneath it and traces the chain across them", async () => {
    // Arrange — one uploaded file that segments into a parent bundle row plus two
    // child deeds, then a chain report over them.
    vi.spyOn(scrutinyApi, "getApplications").mockResolvedValue([buildApplication()]);
    vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: THREAD_ID,
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });
    vi.spyOn(scrutinyApi, "addDocuments").mockResolvedValue([
      buildDocument({
        documentId: "bundle",
        filename: "01_clean_chain.pdf",
        documentTypeId: null,
        documentTypeLabel: "",
        typeConfidence: 0,
        stage: "queued",
        status: "checking",
        pageCount: 0,
      }),
    ]);

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);
    await userEvent.upload(
      screen.getByLabelText(/documents to attach/i),
      new File(["x"], "01_clean_chain.pdf", { type: "application/pdf" }),
    );
    await screen.findByRole("list", { name: /documents ready to verify/i });

    const bundleRow = buildDocument({
      documentId: "bundle",
      filename: "01_clean_chain.pdf",
      documentTypeId: "sale_deed",
      documentTypeLabel: "Sale deed",
      stage: "done",
      status: "verified",
      pageCount: 4,
      checks: [
        buildCheck({
          checkId: "bundle:bundle",
          documentId: "bundle",
          status: "info",
          title: "2 documents found in this file",
        }),
      ],
    });
    const firstDeed = buildDocument({
      documentId: "deed_a",
      filename: "01_clean_chain.pdf",
      documentTypeId: "link_doc",
      documentTypeLabel: "Link document",
      status: "verified",
      parentDocumentId: "bundle",
      pageStart: 0,
      pageEnd: 1,
      deedRecord: bundledDeed({
        docNo: "1188/2003",
        registrationDate: "2003-06-12",
        seller: "Govind Rao",
        buyer: "Ramesh Kumar",
      }),
    });
    const secondDeed = buildDocument({
      documentId: "deed_b",
      filename: "01_clean_chain.pdf",
      documentTypeId: "sale_deed",
      documentTypeLabel: "Sale deed",
      status: "verified",
      parentDocumentId: "bundle",
      pageStart: 2,
      pageEnd: 3,
      deedRecord: bundledDeed({
        docNo: "2451/2011",
        registrationDate: "2011-09-05",
        seller: "Ramesh Kumar",
        buyer: "Sunita Sharma",
      }),
    });

    stubEventStream([
      stepFrame("identify", "running"),
      docFrame(bundleRow),
      docFrame(firstDeed),
      docFrame(secondDeed),
      stepFrame("identify", "done"),
      summaryFrame(buildSummary({ threadStatus: "clear" })),
      chainFrame(
        buildOwnershipReport({
          threadId: THREAD_ID,
          verdict: {
            level: "clean",
            headline: "Title traces cleanly from 2003 to today",
            plain: "Ownership flows through 2 registered deeds with no breaks.",
          },
          chain: {
            overall: "intact",
            counts: { linked: 1 },
            orderedDocumentIds: ["deed_a", "deed_b"],
            excludedDocumentIds: [],
            duplicateDocumentIds: [],
            rolesByDocumentId: { deed_a: "title", deed_b: "title" },
            links: [
              {
                fromDocumentId: "deed_a",
                toDocumentId: "deed_b",
                fromDocNo: "1188/2003",
                toDocNo: "2451/2011",
                verdict: "linked",
                identityScore: 100,
                checks: { identity: true, property: true },
                notes: [],
              },
            ],
            findings: [],
          },
        }),
      ),
      DONE_FRAME,
    ]);

    // Act
    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));
    await waitFor(() =>
      expect(screen.getByText(/finished reading/i)).toBeInTheDocument(),
    );

    // Assert — both child deeds show with their page ranges, and the chain report
    // is present.
    const deedCards = await screen.findAllByRole("article", {
      name: "01_clean_chain.pdf",
    });
    expect(deedCards).toHaveLength(3); // the bundle row + two child deeds
    const record = screen.getByRole("region", { name: /scrutiny record/i });
    expect(record).toHaveTextContent("pp. 1–2");
    expect(record).toHaveTextContent("pp. 3–4");
    expect(
      screen.getByRole("region", { name: /chain of title/i }),
    ).toHaveTextContent("Title traces cleanly from 2003 to today");

    // The chain is the conclusion the run was for, so it comes BEFORE the deed
    // cards that evidence it. Behind three deeds and thirty checks it was missed.
    const chain = screen.getByRole("region", { name: /chain of title/i });
    expect(chain.compareDocumentPosition(deedCards[0])).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    );

    // The timeline runs oldest deed first, and says the hand-over held.
    const timeline = screen.getByRole("list", { name: /ownership timeline/i });
    const deeds = within(timeline).getAllByRole("listitem");
    expect(deeds).toHaveLength(2);
    expect(deeds[0]).toHaveTextContent("1188/2003");
    expect(deeds[1]).toHaveTextContent("2451/2011");
    expect(timeline).toHaveTextContent("ownership carries over");
  });

});

/** One deed out of a bundle, with just enough read off it to place on the timeline. */
function bundledDeed({
  docNo,
  registrationDate,
  seller,
  buyer,
}: {
  docNo: string;
  registrationDate: string;
  seller: string;
  buyer: string;
}): DeedRecord {
  const party = (name: string): Party => ({
    name,
    nameOriginal: null,
    relation: null,
    relativeName: null,
    address: null,
    pan: null,
    aadhaar: null,
  });
  return {
    docNo,
    sro: "SRO Serilingampally",
    registrationDate,
    executionDate: null,
    deedType: "Sale Deed",
    sellers: [party(seller)],
    buyers: [party(buyer)],
    property: {
      surveyNo: "142/2",
      plotNo: "17",
      extentText: "400 Sq. Yards",
      extentSqYard: 400,
      boundaries: null,
      locality: "Kondapur",
      ulpin: null,
    },
    considerationText: "Rs. 6,00,000/-",
    considerationInr: 600_000,
    stampDutyText: null,
    estampNo: null,
    priorDeedRefs: [],
    executedViaGpa: false,
  };
}
