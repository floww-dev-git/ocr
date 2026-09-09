import { useCallback, useState } from "react";

import { ApiError } from "@/api/apiError";
import type {
  CheckResolution,
  DocumentState,
  ScrutinySummary,
} from "@/api/contracts";
import { scrutinyApi } from "@/api/scrutinyApi";

const BUSY_MESSAGE =
  "That document is still being read. Wait for it to finish, then try again.";
const GENERIC_MESSAGE = "That change could not be saved.";

const MESSAGES_BY_CODE: Record<string, string> = {
  DOCUMENT_BUSY: BUSY_MESSAGE,
  DOCUMENT_FIELD_NOT_FOUND: "That detail is not on this document.",
  FIELD_VALUE_NOT_TEXT: "A correction has to be typed as text.",
  FIELD_VALUE_TOO_LONG: "That correction is too long.",
  NOTHING_TO_CONFIRM:
    "There is nothing to sign off yet. Read the document first.",
  CHECK_NOT_RETRYABLE:
    "The department already agreed on this one, so there is nothing to re-ask.",
  ISSUER_CHECK_MISSING:
    "This document was never sent to the department, so there is nothing to re-ask.",
  NO_ISSUER_TO_RETRY:
    "The department that issues this document does not publish a verification " +
    "interface. Verify it against the original and mark it verified by hand.",
  UNKNOWN_CHECK_RESOLUTION: GENERIC_MESSAGE,
  CHECK_NOT_FOUND: "That check is no longer on this scrutiny.",
  THREAD_NOT_FOUND: "That scrutiny no longer exists. Open it again.",
};

export interface OfficerActionsResult {
  busy: boolean;
  problem: string | null;
  dismissProblem: () => void;
  editField: (documentId: string, fieldKey: string, value: string) => void;
  confirmFields: (documentId: string) => void;
  resolveCheck: (checkId: string, action: CheckResolution) => void;
  retryVerification: (documentId: string) => void;
}

export function useOfficerActions(args: {
  threadId: string | null;
  onDocument: (document: DocumentState) => void;
  onSummary: (summary: ScrutinySummary) => void;
}): OfficerActionsResult {
  const { threadId, onDocument, onSummary } = args;
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const perform = useCallback(
    async (
      act: (threadId: string) => Promise<{
        document: DocumentState;
        summary: ScrutinySummary;
      }>,
    ) => {
      if (threadId === null) {
        return;
      }
      setBusy(true);
      setProblem(null);
      try {
        const change = await act(threadId);
        // Every officer action answers with the document AND the whole-thread
        // consequence, so both are taken from the same response rather than
        // re-fetched and risking a mismatched pair.
        onDocument(change.document);
        onSummary(change.summary);
      } catch (error: unknown) {
        setProblem(readActionProblem(error));
        if (!(error instanceof ApiError)) {
          console.error(error);
        }
      } finally {
        setBusy(false);
      }
    },
    [onDocument, onSummary, threadId],
  );

  return {
    busy,
    problem,
    dismissProblem: useCallback(() => setProblem(null), []),
    editField: useCallback(
      (documentId, fieldKey, value) => {
        void perform((id) =>
          scrutinyApi.updateField({ threadId: id, documentId, fieldKey, value }),
        );
      },
      [perform],
    ),
    confirmFields: useCallback(
      (documentId) => {
        void perform((id) => scrutinyApi.confirmFields({ threadId: id, documentId }));
      },
      [perform],
    ),
    resolveCheck: useCallback(
      (checkId, action) => {
        void perform((id) => scrutinyApi.resolveCheck({ threadId: id, checkId, action }));
      },
      [perform],
    ),
    retryVerification: useCallback(
      (documentId) => {
        void perform((id) =>
          scrutinyApi.retryVerification({ threadId: id, documentId }),
        );
      },
      [perform],
    ),
  };
}

function readActionProblem(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return GENERIC_MESSAGE;
  }
  return MESSAGES_BY_CODE[error.errorCode] ?? GENERIC_MESSAGE;
}
