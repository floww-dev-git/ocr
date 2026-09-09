import { describe, expect, it } from "vitest";

import { buildDocument, buildSummary } from "@/test/factories";
import {
  addProblemToAnalysis,
  appendAnalysis,
  appendAttachment,
  appendNote,
  applyEventToAnalysis,
  mintEntryId,
  settleAnalysis,
  type AnalysisEntry,
  type TranscriptEntry,
} from "./transcript";

/** Mirrors the shell: mint the id, then append with it. */
function startAnalysis(entries: TranscriptEntry[]) {
  const id = mintEntryId("analysis");
  return { entries: appendAnalysis(entries, id), id };
}

function analysisAt(entries: TranscriptEntry[], index: number): AnalysisEntry {
  const entry = entries[index];
  if (entry.kind !== "analysis") {
    throw new Error(`entry ${index} is a ${entry.kind}, not an analysis`);
  }
  return entry;
}

describe("the transcript", () => {
  it("starts empty", () => {
    expect(appendAttachment([], ["a.jpg"])).toHaveLength(1);
  });

  it("appends, so the newest entry is always last", () => {
    const first = appendAttachment([], ["one.jpg"]);
    const second = startAnalysis(first);
    const third = appendAttachment(second.entries, ["two.jpg"]);
    const fourth = startAnalysis(third);

    expect(fourth.entries.map((entry) => entry.kind)).toEqual([
      "attachment",
      "analysis",
      "attachment",
      "analysis",
    ]);
  });

  it("gives every entry its own identity", () => {
    const first = startAnalysis([]);
    const second = startAnalysis(first.entries);

    expect(first.id).not.toBe(second.id);
  });

  it("records what the officer submitted, separately from what was made of it", () => {
    const entries = appendAttachment([], ["pan.jpg", "aadhaar.jpg"]);

    expect(entries[0]).toMatchObject({
      kind: "attachment",
      filenames: ["pan.jpg", "aadhaar.jpg"],
    });
  });

  it("keeps a run's documents with that run, not with an earlier one", () => {
    const first = startAnalysis([]);
    let entries = applyEventToAnalysis(first.entries, first.id, {
      type: "doc",
      payload: buildDocument({ documentId: "document_1" }),
    });
    const second = startAnalysis(entries);
    entries = applyEventToAnalysis(second.entries, second.id, {
      type: "doc",
      payload: buildDocument({ documentId: "document_2" }),
    });

    expect(analysisAt(entries, 0).documentIds).toEqual(["document_1"]);
    expect(analysisAt(entries, 1).documentIds).toEqual(["document_2"]);
  });

  it("lists a document once however many times the run reports on it", () => {
    const { entries: started, id } = startAnalysis([]);
    let entries = started;
    for (const stage of ["identifying", "extracting", "done"] as const) {
      entries = applyEventToAnalysis(entries, id, {
        type: "doc",
        payload: buildDocument({ documentId: "document_1", stage }),
      });
    }

    expect(analysisAt(entries, 0).documentIds).toEqual(["document_1"]);
  });

  it("routes step progress to the run it belongs to", () => {
    const first = startAnalysis([]);
    const second = startAnalysis(first.entries);
    const entries = applyEventToAnalysis(second.entries, second.id, {
      type: "step",
      payload: { step: "identify", state: "running" },
    });

    expect(analysisAt(entries, 0).run.steps).toEqual([]);
    expect(analysisAt(entries, 1).run.steps).toHaveLength(1);
  });

  it("leaves an earlier run untouched when a later one finishes", () => {
    const first = startAnalysis([]);
    let entries = applyEventToAnalysis(first.entries, first.id, { type: "done" });
    const second = startAnalysis(entries);
    entries = applyEventToAnalysis(second.entries, second.id, {
      type: "step",
      payload: { step: "verify", state: "running" },
    });

    expect(analysisAt(entries, 0).run.finished).toBe(true);
    expect(analysisAt(entries, 0).run.steps).toEqual([]);
  });

  it("keeps a problem with the run that hit it", () => {
    const first = startAnalysis([]);
    const second = startAnalysis(first.entries);
    const entries = addProblemToAnalysis(
      second.entries,
      second.id,
      "the connection was lost",
    );

    expect(analysisAt(entries, 0).run.problems).toEqual([]);
    expect(analysisAt(entries, 1).run.problems).toEqual([
      "the connection was lost",
    ]);
  });

  it("settles a run that never got its closing frame", () => {
    const { entries: started, id } = startAnalysis([]);
    const entries = settleAnalysis(started, id);

    expect(analysisAt(entries, 0).run.running).toBe(false);
    expect(analysisAt(entries, 0).run.finished).toBe(true);
  });

  it("leaves an already-finished run alone when settling", () => {
    const { entries: started, id } = startAnalysis([]);
    const finished = applyEventToAnalysis(started, id, { type: "done" });

    expect(settleAnalysis(finished, id)).toEqual(finished);
  });

  it("ignores an id that is not in the transcript", () => {
    const { entries } = startAnalysis([]);

    expect(applyEventToAnalysis(entries, "analysis_missing", { type: "done" })).toEqual(
      entries,
    );
  });

  it("never targets an attachment entry with a run's events", () => {
    const attachment = appendAttachment([], ["a.jpg"]);
    const entries = applyEventToAnalysis(attachment, attachment[0].id, {
      type: "done",
    });

    expect(entries).toEqual(attachment);
  });

  it("appends a note as its own entry, leaving an earlier note in place", () => {
    const first = appendNote([], "the first note");
    const second = appendNote(first, "the second note");

    expect(second.map((entry) => (entry as NoteEntryLike).text)).toEqual([
      "the first note",
      "the second note",
    ]);
  });

  it("carries a run's closing summary on the run itself", () => {
    const { entries: started, id } = startAnalysis([]);
    const entries = applyEventToAnalysis(started, id, {
      type: "summary",
      payload: buildSummary({ threadStatus: "attention" }),
    });

    expect(analysisAt(entries, 0).run.summary?.threadStatus).toBe("attention");
  });
});

interface NoteEntryLike {
  text: string;
}
