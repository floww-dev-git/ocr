import { describe, expect, it } from "vitest";

import type { AnalysisEvent } from "@/api/contracts";
import {
  applyAnalysisEvent,
  groupDocuments,
  IDLE_RUN,
  readCurrentStep,
  readStepsInOrder,
  startRun,
} from "./analysisRunState";
import {
  buildDocument,
  buildOwnershipReport,
  buildSummary,
} from "@/test/factories";

function fold(events: AnalysisEvent[]) {
  return events.reduce(applyAnalysisEvent, startRun());
}

const IDENTIFY_RUNNING: AnalysisEvent = {
  type: "step",
  payload: { step: "identify", state: "running" },
};
const IDENTIFY_DONE: AnalysisEvent = {
  type: "step",
  payload: { step: "identify", state: "done" },
};

describe("the analysis run state", () => {
  it("starts idle before anything is asked for", () => {
    expect(IDLE_RUN.running).toBe(false);
    expect(IDLE_RUN.finished).toBe(false);
  });

  it("is running as soon as the officer starts it", () => {
    expect(startRun().running).toBe(true);
  });

  it("records a step as it starts", () => {
    const state = fold([IDENTIFY_RUNNING]);

    expect(state.steps).toEqual([
      { step: "identify", state: "running", checkCount: null },
    ]);
  });

  it("moves a step to done in place rather than listing it twice", () => {
    const state = fold([IDENTIFY_RUNNING, IDENTIFY_DONE]);

    expect(state.steps).toEqual([
      { step: "identify", state: "done", checkCount: null },
    ]);
  });

  it("keeps how many checks the run produced", () => {
    const state = fold([
      { type: "step", payload: { step: "checks", state: "running" } },
      { type: "step", payload: { step: "checks", state: "done", count: 8 } },
    ]);

    expect(state.steps[0].checkCount).toBe(8);
  });

  it("does not lose an earlier count when a second document repeats the step", () => {
    const state = fold([
      { type: "step", payload: { step: "checks", state: "done", count: 8 } },
      { type: "step", payload: { step: "checks", state: "running" } },
    ]);

    expect(state.steps[0]).toEqual({
      step: "checks",
      state: "running",
      checkCount: 8,
    });
  });

  it("collects each document once, keeping the latest version of it", () => {
    const state = fold([
      { type: "doc", payload: buildDocument({ stage: "identifying" }) },
      { type: "doc", payload: buildDocument({ stage: "extracting" }) },
      { type: "doc", payload: buildDocument({ stage: "done" }) },
    ]);

    expect(state.documents).toHaveLength(1);
    expect(state.documents[0].stage).toBe("done");
  });

  it("keeps several documents apart", () => {
    const state = fold([
      { type: "doc", payload: buildDocument({ documentId: "document_1" }) },
      { type: "doc", payload: buildDocument({ documentId: "document_2" }) },
    ]);

    expect(state.documents.map((document) => document.documentId)).toEqual([
      "document_1",
      "document_2",
    ]);
  });

  it("takes the closing summary", () => {
    const state = fold([
      { type: "summary", payload: buildSummary({ threadStatus: "attention" }) },
    ]);

    expect(state.summary?.threadStatus).toBe("attention");
  });

  it("starts with no ownership report", () => {
    expect(IDLE_RUN.ownershipReport).toBeNull();
  });

  it("takes the chain-of-title report when it arrives", () => {
    const state = fold([
      {
        type: "chain",
        payload: buildOwnershipReport({
          verdict: {
            level: "broken",
            headline: "The title chain is broken",
            plain: "A hand-off does not connect.",
          },
        }),
      },
    ]);

    expect(state.ownershipReport?.verdict.level).toBe("broken");
  });

  it("leaves the ownership report null for a thread that has no deeds", () => {
    const state = fold([
      { type: "doc", payload: buildDocument() },
      { type: "summary", payload: buildSummary() },
      { type: "done" },
    ]);

    expect(state.ownershipReport).toBeNull();
  });

  it("stops running once the stream closes", () => {
    const state = fold([IDENTIFY_RUNNING, { type: "done" }]);

    expect(state.running).toBe(false);
    expect(state.finished).toBe(true);
  });

  it("keeps a problem beside the results rather than replacing them", () => {
    const state = fold([
      { type: "doc", payload: buildDocument() },
      { type: "error", payload: { message: "broken.pdf could not be read." } },
      { type: "done" },
    ]);

    expect(state.documents).toHaveLength(1);
    expect(state.problems).toEqual(["broken.pdf could not be read."]);
  });

  it("keeps every problem when more than one document fails", () => {
    const state = fold([
      { type: "error", payload: { message: "first failed" } },
      { type: "error", payload: { message: "second failed" } },
    ]);

    expect(state.problems).toEqual(["first failed", "second failed"]);
  });

  it("names the step the officer is waiting on", () => {
    const state = fold([
      IDENTIFY_DONE,
      { type: "step", payload: { step: "verify", state: "running" } },
    ]);

    expect(readCurrentStep(state)).toBe("verify");
  });

  it("names nothing once the run has settled", () => {
    const state = fold([IDENTIFY_DONE, { type: "done" }]);

    expect(readCurrentStep(state)).toBeNull();
  });

  it("lists the steps in the order the backend performs them", () => {
    // Arrive deliberately out of order to prove the display order is not
    // whatever the network delivered.
    const state = fold([
      { type: "step", payload: { step: "verify", state: "done" } },
      { type: "step", payload: { step: "identify", state: "done" } },
      { type: "step", payload: { step: "checks", state: "done" } },
      { type: "step", payload: { step: "extract", state: "done" } },
    ]);

    expect(readStepsInOrder(state).map((step) => step.step)).toEqual([
      "identify",
      "extract",
      "checks",
      "verify",
    ]);
  });

  it("lists only the steps that actually happened", () => {
    const state = fold([IDENTIFY_RUNNING]);

    expect(readStepsInOrder(state).map((step) => step.step)).toEqual(["identify"]);
  });
});

describe("grouping documents the way the officer reads them", () => {
  it("nests the documents found in a bundle beneath the file they came from", () => {
    const bundle = buildDocument({ documentId: "bundle", filename: "chain.pdf" });
    const first = buildDocument({
      documentId: "deed_1",
      parentDocumentId: "bundle",
      pageStart: 0,
      pageEnd: 1,
    });
    const second = buildDocument({
      documentId: "deed_2",
      parentDocumentId: "bundle",
      pageStart: 2,
      pageEnd: 3,
    });

    const groups = groupDocuments([bundle, first, second]);

    expect(groups).toHaveLength(1);
    expect(groups[0].document.documentId).toBe("bundle");
    expect(groups[0].children.map((child) => child.documentId)).toEqual([
      "deed_1",
      "deed_2",
    ]);
  });

  it("orders the children by the page they start on, not their arrival", () => {
    const bundle = buildDocument({ documentId: "bundle" });
    const later = buildDocument({
      documentId: "deed_later",
      parentDocumentId: "bundle",
      pageStart: 4,
      pageEnd: 5,
    });
    const earlier = buildDocument({
      documentId: "deed_earlier",
      parentDocumentId: "bundle",
      pageStart: 0,
      pageEnd: 1,
    });

    const groups = groupDocuments([bundle, later, earlier]);

    expect(groups[0].children.map((child) => child.documentId)).toEqual([
      "deed_earlier",
      "deed_later",
    ]);
  });

  it("leaves a lone document standing on its own with no children", () => {
    const groups = groupDocuments([buildDocument({ documentId: "pan" })]);

    expect(groups).toHaveLength(1);
    expect(groups[0].children).toEqual([]);
  });

  it("keeps unrelated files as separate groups in the order attached", () => {
    const groups = groupDocuments([
      buildDocument({ documentId: "pan" }),
      buildDocument({ documentId: "aadhaar" }),
    ]);

    expect(groups.map((group) => group.document.documentId)).toEqual([
      "pan",
      "aadhaar",
    ]);
  });
});
