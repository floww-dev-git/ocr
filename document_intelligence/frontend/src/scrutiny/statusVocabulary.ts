import type {
  CheckStatus,
  DocumentStage,
  DocumentStatus,
  ThreadStatus,
} from "@/api/contracts";

export type Tone =
  | "pass"
  | "warn"
  | "fail"
  | "info"
  | "pending"
  | "unavailable"
  | "neutral"
  | "ai";

export interface StatusReading {
  tone: Tone;
  label: string;
}

/**
 * The single place a machine status becomes words an officer reads. Wording is
 * plain and states what is true, never a euphemism: an `unavailable` check says
 * the department could not be reached, it does not say "pending".
 */
const CHECK_READINGS: Record<CheckStatus, StatusReading> = {
  pass: { tone: "pass", label: "Agrees" },
  warn: { tone: "warn", label: "Needs a look" },
  fail: { tone: "fail", label: "Does not agree" },
  info: { tone: "info", label: "For information" },
  pending: { tone: "pending", label: "Not checked yet" },
  unavailable: { tone: "unavailable", label: "Could not check" },
};

const DOCUMENT_READINGS: Record<DocumentStatus, StatusReading> = {
  checking: { tone: "ai", label: "Reading" },
  failed: { tone: "fail", label: "Does not agree" },
  unavailable: { tone: "unavailable", label: "Could not verify" },
  attention: { tone: "warn", label: "Needs a look" },
  verified: { tone: "pass", label: "Verified" },
};

const THREAD_READINGS: Record<ThreadStatus, StatusReading> = {
  new: { tone: "neutral", label: "Nothing attached" },
  running: { tone: "ai", label: "Reading" },
  attention: { tone: "warn", label: "Needs a look" },
  clear: { tone: "pass", label: "Clear" },
};

const STAGE_LABELS: Record<DocumentStage, string> = {
  queued: "Waiting",
  identifying: "Identifying the document",
  extracting: "Reading the details",
  checking: "Comparing against the application",
  verifying: "Asking the department",
  done: "Finished",
};

export function readCheckStatus(status: CheckStatus): StatusReading {
  return CHECK_READINGS[status] ?? CHECK_READINGS.pending;
}

export function readDocumentStatus(status: DocumentStatus): StatusReading {
  return DOCUMENT_READINGS[status] ?? DOCUMENT_READINGS.checking;
}

export function readThreadStatus(status: ThreadStatus): StatusReading {
  return THREAD_READINGS[status] ?? THREAD_READINGS.new;
}

export function readStageLabel(stage: DocumentStage): string {
  return STAGE_LABELS[stage] ?? STAGE_LABELS.queued;
}
