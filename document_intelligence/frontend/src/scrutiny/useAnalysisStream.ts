import { useCallback, useEffect, useRef } from "react";

import type { AnalysisEvent } from "@/api/contracts";
import { scrutinyApi } from "@/api/scrutinyApi";
import { streamAnalysis } from "./streamAnalysis";

export const STREAM_FAILED_MESSAGE =
  "The connection to the reader was lost. Start the analysis again.";

export interface AnalysisStreamHandlers {
  threadId: string | null;
  onEvent: (event: AnalysisEvent) => void;
  onFailure: (message: string) => void;
  /** Always called once a run stops, however it stopped. */
  onSettled: () => void;
}

/**
 * Owns the connection and nothing else. The events are handed straight to the
 * caller so the transcript stays the only place a run's state is kept — there is
 * no second copy here to drift from it.
 */
export function useAnalysisStream({
  threadId,
  onEvent,
  onFailure,
  onSettled,
}: AnalysisStreamHandlers) {
  const abortRef = useRef<AbortController | null>(null);
  const handlers = useRef({ onEvent, onFailure, onSettled });
  handlers.current = { onEvent, onFailure, onSettled };

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  // Leaving the thread, or unmounting, closes the stream. The backend settles a
  // half-read document on its side when that happens (ADR-008 D5).
  useEffect(() => abort, [abort, threadId]);

  const start = useCallback(() => {
    if (threadId === null) {
      return;
    }
    abort();
    const controller = new AbortController();
    abortRef.current = controller;

    void streamAnalysis({
      url: scrutinyApi.analyzeUrl(threadId),
      signal: controller.signal,
      onEvent: (event) => handlers.current.onEvent(event),
    })
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        console.error(error);
        handlers.current.onFailure(STREAM_FAILED_MESSAGE);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          handlers.current.onSettled();
        }
      });
  }, [abort, threadId]);

  return { start, abort };
}
