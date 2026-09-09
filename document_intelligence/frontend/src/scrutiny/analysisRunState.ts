import type {
  AnalysisEvent,
  AnalysisStep,
  DocumentState,
  OwnershipReport,
  ScrutinySummary,
  StepState,
} from "@/api/contracts";
import { ANALYSIS_STEPS } from "@/api/contracts";

export interface StepProgress {
  step: AnalysisStep;
  state: StepState;
  checkCount: number | null;
}

export interface AnalysisRunState {
  running: boolean;
  finished: boolean;
  steps: StepProgress[];
  documents: DocumentState[];
  summary: ScrutinySummary | null;
  // Only a thread holding registered deeds gets one; it arrives after the summary.
  ownershipReport: OwnershipReport | null;
  problems: string[];
}

export const IDLE_RUN: AnalysisRunState = {
  running: false,
  finished: false,
  steps: [],
  documents: [],
  summary: null,
  ownershipReport: null,
  problems: [],
};

export function startRun(): AnalysisRunState {
  return { ...IDLE_RUN, running: true };
}

/**
 * Folds one event into the run's state.
 *
 * Written as a pure reducer so the whole live-activity behaviour can be tested
 * against a recorded frame sequence, with no network and no React.
 */
export function applyAnalysisEvent(
  state: AnalysisRunState,
  event: AnalysisEvent,
): AnalysisRunState {
  switch (event.type) {
    case "step":
      return { ...state, steps: mergeStep(state.steps, event.payload) };
    case "doc":
      return { ...state, documents: mergeDocument(state.documents, event.payload) };
    case "summary":
      return { ...state, summary: event.payload };
    case "chain":
      return { ...state, ownershipReport: event.payload };
    case "error":
      // Kept alongside the results rather than replacing them: the run may have
      // read three documents and failed on the fourth, and the officer needs both.
      return { ...state, problems: [...state.problems, event.payload.message] };
    case "done":
      return { ...state, running: false, finished: true };
    default:
      return state;
  }
}

function mergeStep(
  steps: StepProgress[],
  payload: { step: AnalysisStep; state: StepState; count?: number },
): StepProgress[] {
  const incoming: StepProgress = {
    step: payload.step,
    state: payload.state,
    checkCount: payload.count ?? null,
  };
  const at = steps.findIndex((existing) => existing.step === payload.step);
  if (at === -1) {
    return [...steps, incoming];
  }
  // A step reappears when a second document is read; the later state wins but
  // an earlier count is not thrown away.
  const next = [...steps];
  next[at] = { ...incoming, checkCount: incoming.checkCount ?? steps[at].checkCount };
  return next;
}

function mergeDocument(
  documents: DocumentState[],
  incoming: DocumentState,
): DocumentState[] {
  const at = documents.findIndex(
    (existing) => existing.documentId === incoming.documentId,
  );
  if (at === -1) {
    return [...documents, incoming];
  }
  const next = [...documents];
  next[at] = incoming;
  return next;
}

export interface DocumentGroup {
  /** The attached file. For a bundle, the parent row; for a lone document, itself. */
  document: DocumentState;
  /** The documents found inside a bundle, in page order. Empty for a lone document. */
  children: DocumentState[];
}

/**
 * The documents as the officer reads them: each attached file, with anything found
 * inside it nested beneath. A bundle that was segmented shows its children under it;
 * everything else stands alone.
 */
export function groupDocuments(documents: DocumentState[]): DocumentGroup[] {
  const childrenByParent = new Map<string, DocumentState[]>();
  for (const document of documents) {
    if (document.parentDocumentId === null) {
      continue;
    }
    const siblings = childrenByParent.get(document.parentDocumentId) ?? [];
    siblings.push(document);
    childrenByParent.set(document.parentDocumentId, siblings);
  }
  return documents
    .filter((document) => document.parentDocumentId === null)
    .map((document) => ({
      document,
      children: [...(childrenByParent.get(document.documentId) ?? [])].sort(
        byPageStart,
      ),
    }));
}

function byPageStart(left: DocumentState, right: DocumentState): number {
  return (left.pageStart ?? 0) - (right.pageStart ?? 0);
}

/** The step the officer is waiting on, for the "still working" line. */
export function readCurrentStep(state: AnalysisRunState): AnalysisStep | null {
  const running = state.steps.find((step) => step.state === "running");
  return running?.step ?? null;
}

/** Steps in the order the backend performs them, whether or not they arrived. */
export function readStepsInOrder(state: AnalysisRunState): StepProgress[] {
  const bySlot = new Map(state.steps.map((step) => [step.step, step]));
  return ANALYSIS_STEPS.filter((step) => bySlot.has(step)).map(
    (step) => bySlot.get(step) as StepProgress,
  );
}
