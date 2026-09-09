import { vi } from "vitest";

/**
 * Serves a scripted SSE body through fetch, one frame per chunk, so a test drives
 * the same code path production uses: fetch -> ReadableStream -> SseFrameReader.
 * Nothing about the parsing or the reducer is stubbed out.
 */
export function stubEventStream(frames: string[]) {
  const encoder = new TextEncoder();
  return vi.spyOn(globalThis, "fetch").mockImplementation(() =>
    Promise.resolve(
      new Response(
        new ReadableStream<Uint8Array>({
          start(controller) {
            for (const frame of frames) {
              controller.enqueue(encoder.encode(frame));
            }
            controller.close();
          },
        }),
        { status: 200, headers: { "Content-Type": "text/event-stream" } },
      ),
    ),
  );
}

export function stepFrame(
  step: string,
  state: "running" | "done",
  count?: number,
): string {
  const payload: Record<string, unknown> = { step, state };
  if (count !== undefined) {
    payload.count = count;
  }
  return `event: step\ndata: ${JSON.stringify(payload)}\n\n`;
}

export function docFrame(document: unknown): string {
  return `event: doc\ndata: ${JSON.stringify(document)}\n\n`;
}

export function summaryFrame(summary: unknown): string {
  return `event: summary\ndata: ${JSON.stringify(summary)}\n\n`;
}

export function errorFrame(message: string): string {
  return `event: error\ndata: ${JSON.stringify({ message })}\n\n`;
}

export function chainFrame(report: unknown): string {
  return `event: chain\ndata: ${JSON.stringify(report)}\n\n`;
}

export const DONE_FRAME = 'event: done\ndata: {"ok":true}\n\n';
