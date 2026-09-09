import { describe, expect, it } from "vitest";

import { readAnalysisEvent } from "./analysisEvents";

describe("readAnalysisEvent", () => {
  it("reads a step frame", () => {
    const event = readAnalysisEvent({
      event: "step",
      data: '{"step":"identify","state":"running"}',
    });

    expect(event).toEqual({
      type: "step",
      payload: { step: "identify", state: "running" },
    });
  });

  it("keeps the check count the backend sends as `count`", () => {
    const event = readAnalysisEvent({
      event: "step",
      data: '{"step":"checks","state":"done","count":8}',
    });

    expect(event).toEqual({
      type: "step",
      payload: { step: "checks", state: "done", count: 8 },
    });
  });

  it("reads a document frame whose payload is the document itself", () => {
    const event = readAnalysisEvent({
      event: "doc",
      data: '{"documentId":"document_1","stage":"done"}',
    });

    expect(event?.type).toBe("doc");
    expect(event).toMatchObject({ payload: { documentId: "document_1" } });
  });

  it("reads a summary frame", () => {
    const event = readAnalysisEvent({
      event: "summary",
      data: '{"threadStatus":"attention","openItems":[]}',
    });

    expect(event).toMatchObject({
      type: "summary",
      payload: { threadStatus: "attention" },
    });
  });

  it("reads a chain frame carrying the ownership report", () => {
    const event = readAnalysisEvent({
      event: "chain",
      data: '{"threadId":"thread_1","verdict":{"level":"broken","headline":"The title chain is broken","plain":"x"}}',
    });

    expect(event?.type).toBe("chain");
    expect(event).toMatchObject({
      payload: { verdict: { level: "broken" } },
    });
  });

  it("reads an error frame's message", () => {
    const event = readAnalysisEvent({
      event: "error",
      data: '{"message":"That document could not be read."}',
    });

    expect(event).toEqual({
      type: "error",
      payload: { message: "That document could not be read." },
    });
  });

  it("reads the closing frame without needing its payload", () => {
    expect(readAnalysisEvent({ event: "done", data: '{"ok":true}' })).toEqual({
      type: "done",
    });
  });

  it("skips a frame type this build does not know", () => {
    expect(readAnalysisEvent({ event: "invented", data: "{}" })).toBeNull();
  });

  it("skips a payload that will not parse rather than failing the run", () => {
    expect(readAnalysisEvent({ event: "doc", data: '{"truncated"' })).toBeNull();
  });

  it("skips a payload that parsed to something that is not an object", () => {
    expect(readAnalysisEvent({ event: "summary", data: "42" })).toBeNull();
  });

  it("skips a frame with no payload at all", () => {
    expect(readAnalysisEvent({ event: "doc", data: "" })).toBeNull();
  });
});
