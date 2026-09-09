import type {
  AnalysisEvent,
  DocumentState,
  ErrorFramePayload,
  OwnershipReport,
  ScrutinySummary,
  StepFramePayload,
} from "@/api/contracts";
import type { SseFrame } from "./sseFrameReader";

/**
 * Turns a raw frame into a typed event, or null if this build cannot use it.
 *
 * An unrecognised tag is skipped rather than thrown: a newer backend adding a
 * frame type must not take the whole run down in an older tab. A payload that
 * will not parse is skipped for the same reason.
 */
export function readAnalysisEvent(frame: SseFrame): AnalysisEvent | null {
  if (frame.event === "done") {
    return { type: "done" };
  }
  const payload = parseJsonOrNull(frame.data);
  if (payload === null) {
    return null;
  }
  switch (frame.event) {
    case "step":
      return { type: "step", payload: payload as StepFramePayload };
    case "doc":
      return { type: "doc", payload: payload as DocumentState };
    case "summary":
      return { type: "summary", payload: payload as ScrutinySummary };
    case "chain":
      return { type: "chain", payload: payload as OwnershipReport };
    case "error":
      return { type: "error", payload: payload as ErrorFramePayload };
    default:
      return null;
  }
}

function parseJsonOrNull(data: string): object | null {
  if (data.length === 0) {
    return null;
  }
  try {
    const parsed: unknown = JSON.parse(data);
    return typeof parsed === "object" && parsed !== null ? parsed : null;
  } catch {
    // A truncated payload is not worth guessing at; the run reports the frames
    // it could read and the closing summary corrects any gap.
    return null;
  }
}
