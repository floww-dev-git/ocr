import { describe, expect, it } from "vitest";

import { SseFrameReader } from "./sseFrameReader";

describe("SseFrameReader", () => {
  it("reads a whole frame the server sent in one piece", () => {
    const reader = new SseFrameReader();

    const frames = reader.read('event: step\ndata: {"step":"identify"}\n\n');

    expect(frames).toEqual([{ event: "step", data: '{"step":"identify"}' }]);
  });

  it("reads several frames arriving together", () => {
    const reader = new SseFrameReader();

    const frames = reader.read(
      'event: step\ndata: {"a":1}\n\nevent: doc\ndata: {"b":2}\n\n',
    );

    expect(frames.map((frame) => frame.event)).toEqual(["step", "doc"]);
  });

  it("holds back a frame split across chunks until it is whole", () => {
    const reader = new SseFrameReader();

    expect(reader.read("event: step\nda")).toEqual([]);
    expect(reader.read('ta: {"step":"ide')).toEqual([]);
    expect(reader.read('ntify"}\n\n')).toEqual([
      { event: "step", data: '{"step":"identify"}' },
    ]);
  });

  it("survives a chunk boundary landing inside the separator", () => {
    const reader = new SseFrameReader();

    expect(reader.read('event: doc\ndata: {"a":1}\n')).toEqual([]);
    expect(reader.read('\nevent: done\ndata: {"ok":true}\n\n')).toEqual([
      { event: "doc", data: '{"a":1}' },
      { event: "done", data: '{"ok":true}' },
    ]);
  });

  it("keeps a payload that itself contains a single newline", () => {
    const reader = new SseFrameReader();

    const frames = reader.read("event: note\ndata: first\ndata: second\n\n");

    expect(frames).toEqual([{ event: "note", data: "first\nsecond" }]);
  });

  it("ignores keep-alive comments", () => {
    const reader = new SseFrameReader();

    const frames = reader.read(": keep alive\n\nevent: done\ndata: {}\n\n");

    expect(frames).toEqual([{ event: "done", data: "{}" }]);
  });

  it("tolerates a field written without the optional space", () => {
    const reader = new SseFrameReader();

    expect(reader.read("event:done\ndata:{}\n\n")).toEqual([
      { event: "done", data: "{}" },
    ]);
  });

  it("tolerates carriage returns from a proxy that rewrites line endings", () => {
    const reader = new SseFrameReader();

    const frames = reader.read('event: step\r\ndata: {"a":1}\r\n\r\n');

    expect(frames).toEqual([{ event: "step", data: '{"a":1}' }]);
  });

  it("survives a chunk boundary splitting a carriage-return pair", () => {
    const reader = new SseFrameReader();

    expect(reader.read('event: step\r\ndata: {"a":1}\r\n\r')).toEqual([]);
    expect(reader.read("\n")).toEqual([{ event: "step", data: '{"a":1}' }]);
  });

  it("returns a final frame the server never terminated", () => {
    const reader = new SseFrameReader();
    reader.read('event: done\ndata: {"ok":true}');

    expect(reader.flush()).toEqual([{ event: "done", data: '{"ok":true}' }]);
  });

  it("flushes nothing when the stream ended cleanly", () => {
    const reader = new SseFrameReader();
    reader.read("event: done\ndata: {}\n\n");

    expect(reader.flush()).toEqual([]);
  });

  it("does not invent a frame from trailing whitespace", () => {
    const reader = new SseFrameReader();
    reader.read("event: done\ndata: {}\n\n\n");

    expect(reader.flush()).toEqual([]);
  });
});
