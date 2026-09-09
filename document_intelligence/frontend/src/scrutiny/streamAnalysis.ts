import type { AnalysisEvent } from "@/api/contracts";
import { readAnalysisEvent } from "./analysisEvents";
import { SseFrameReader } from "./sseFrameReader";

/**
 * Reads the analyze stream with fetch + ReadableStream rather than EventSource.
 *
 * EventSource reconnects on its own. On this endpoint a reconnect mid-run starts
 * a second analysis of the same thread, which re-bills every Gemini call and
 * re-asks the Income Tax Department a question already in flight (recorded as a
 * known, unguarded hazard in backend ADR-008). An AbortController-driven fetch
 * reconnects only when this code decides to, so a flaky network cannot quietly
 * double the work.
 */
export async function streamAnalysis(args: {
  url: string;
  signal: AbortSignal;
  onEvent: (event: AnalysisEvent) => void;
}): Promise<void> {
  const { url, signal, onEvent } = args;
  const response = await fetch(url, {
    signal,
    headers: { Accept: "text/event-stream" },
  });

  if (!response.ok || response.body === null) {
    throw new Error(`The analysis stream did not open (HTTP ${response.status})`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  const frames = new SseFrameReader();

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      // stream:true so a multi-byte character split across chunks is not
      // decoded into a replacement character mid-name.
      emit(frames.read(decoder.decode(value, { stream: true })), onEvent);
    }
    emit(frames.read(decoder.decode()), onEvent);
    emit(frames.flush(), onEvent);
  } finally {
    reader.releaseLock();
  }
}

function emit(
  frames: ReturnType<SseFrameReader["read"]>,
  onEvent: (event: AnalysisEvent) => void,
): void {
  for (const frame of frames) {
    const event = readAnalysisEvent(frame);
    if (event !== null) {
      onEvent(event);
    }
  }
}
