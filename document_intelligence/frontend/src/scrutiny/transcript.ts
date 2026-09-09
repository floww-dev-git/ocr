import type { AnalysisEvent, DocumentState, ScrutinySummary } from "@/api/contracts";
import {
  applyAnalysisEvent,
  startRun,
  type AnalysisRunState,
} from "./analysisRunState";

export interface GreetingEntry {
  kind: "greeting";
  id: string;
  text: string;
}

export interface AttachmentEntry {
  kind: "attachment";
  id: string;
  filenames: string[];
}

export interface AnalysisEntry {
  kind: "analysis";
  id: string;
  run: AnalysisRunState;
  /** Only the documents this run read, so a card sits with the run that made it. */
  documentIds: string[];
}

export interface NoteEntry {
  kind: "note";
  id: string;
  text: string;
}

export type TranscriptEntry =
  | GreetingEntry
  | AttachmentEntry
  | AnalysisEntry
  | NoteEntry;

const BLANK_GREETING =
  "This is a new scrutiny. Fill in the application details on the right, then " +
  "attach the applicant's documents.";

/** The prototype's opening line, keyed on whether the application is named yet. */
export function readGreeting(
  applicationId: string,
  applicantName: string | null,
): string {
  if (applicantName === null || applicantName.length === 0) {
    return BLANK_GREETING;
  }
  return (
    `I'm ready to scrutinize ${applicationId} for ${applicantName}.\n` +
    "Attach the applicant's documents, or load the sample set to see how this works."
  );
}

export function greetingEntry(text: string): GreetingEntry {
  return { kind: "greeting", id: mintEntryId("greeting"), text };
}

let entrySequence = 0;

/**
 * Identity is minted by the caller, not inside an append.
 *
 * The shell has to know a run's id *before* the stream can start, and a React
 * state updater is no place to produce it: updaters must stay pure and may run
 * more than once. Handing the id in keeps the append a pure function of its
 * arguments.
 */
export function mintEntryId(kind: TranscriptEntry["kind"]): string {
  return `${kind}_${entrySequence++}`;
}

/**
 * The workspace as a record of what happened, in the order it happened.
 *
 * Everything appends. An officer's later correction updates the document where it
 * already sits rather than moving it, because the card belongs to the run that
 * produced it and relocating it would falsify the order of events.
 */
export function appendAttachment(
  entries: TranscriptEntry[],
  filenames: string[],
): TranscriptEntry[] {
  return [
    ...entries,
    { kind: "attachment", id: mintEntryId("attachment"), filenames },
  ];
}

export function appendAnalysis(
  entries: TranscriptEntry[],
  id: string,
): TranscriptEntry[] {
  return [...entries, { kind: "analysis", id, run: startRun(), documentIds: [] }];
}

export function appendNote(
  entries: TranscriptEntry[],
  text: string,
): TranscriptEntry[] {
  return [...entries, { kind: "note", id: mintEntryId("note"), text }];
}

export function applyEventToAnalysis(
  entries: TranscriptEntry[],
  id: string,
  event: AnalysisEvent,
): TranscriptEntry[] {
  return mapAnalysis(entries, id, (entry) => ({
    ...entry,
    run: applyAnalysisEvent(entry.run, event),
    documentIds:
      event.type === "doc"
        ? rememberDocument(entry.documentIds, event.payload.documentId)
        : entry.documentIds,
  }));
}

export function addProblemToAnalysis(
  entries: TranscriptEntry[],
  id: string,
  message: string,
): TranscriptEntry[] {
  return mapAnalysis(entries, id, (entry) => ({
    ...entry,
    run: { ...entry.run, problems: [...entry.run.problems, message] },
  }));
}

/** Stops an entry claiming work is in progress once the stream is over. */
export function settleAnalysis(
  entries: TranscriptEntry[],
  id: string,
): TranscriptEntry[] {
  return mapAnalysis(entries, id, (entry) =>
    entry.run.running
      ? { ...entry, run: { ...entry.run, running: false, finished: true } }
      : entry,
  );
}

export function readDocumentsFromEvent(
  event: AnalysisEvent,
): DocumentState | null {
  return event.type === "doc" ? event.payload : null;
}

export function readSummaryFromEvent(
  event: AnalysisEvent,
): ScrutinySummary | null {
  return event.type === "summary" ? event.payload : null;
}

function mapAnalysis(
  entries: TranscriptEntry[],
  id: string,
  change: (entry: AnalysisEntry) => AnalysisEntry,
): TranscriptEntry[] {
  return entries.map((entry) =>
    entry.kind === "analysis" && entry.id === id ? change(entry) : entry,
  );
}

function rememberDocument(documentIds: string[], documentId: string): string[] {
  return documentIds.includes(documentId)
    ? documentIds
    : [...documentIds, documentId];
}
