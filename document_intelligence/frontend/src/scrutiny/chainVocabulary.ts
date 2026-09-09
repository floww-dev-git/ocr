import type {
  FindingSeverity,
  LinkVerdict,
  ReportVerdictLevel,
  RiskLevel,
} from "@/api/contracts";
import type { Tone } from "./statusVocabulary";

/**
 * The one place a chain verdict becomes a tone the UI can paint. The backend
 * sends verdicts and labels as words, deliberately, so which colour or icon to
 * show is decided here rather than baked into the payload.
 */
const LINK_VERDICT_TONES: Record<LinkVerdict, Tone> = {
  linked: "pass",
  weak: "warn",
  gap: "warn",
  broken: "fail",
};

const REPORT_VERDICT_TONES: Record<ReportVerdictLevel, Tone> = {
  clean: "pass",
  review: "warn",
  broken: "fail",
};

const RISK_TONES: Record<RiskLevel, Tone> = {
  Low: "pass",
  Medium: "warn",
  High: "fail",
};

const SEVERITY_TONES: Record<FindingSeverity, Tone> = {
  high: "fail",
  medium: "warn",
  low: "warn",
  clear: "pass",
};

export function readLinkVerdictTone(verdict: string): Tone {
  return LINK_VERDICT_TONES[verdict as LinkVerdict] ?? "neutral";
}

export function readReportVerdictTone(level: ReportVerdictLevel): Tone {
  return REPORT_VERDICT_TONES[level] ?? "neutral";
}

export function readRiskTone(level: RiskLevel): Tone {
  return RISK_TONES[level] ?? "neutral";
}

export function readSeverityTone(severity: FindingSeverity): Tone {
  return SEVERITY_TONES[severity] ?? "neutral";
}

/**
 * A hand-off that did not carry ownership over gets a heading of its own rather
 * than the same badge a healthy one wears. A break is the finding the whole report
 * exists to surface, so it must not read as one more row in a list.
 */
const RUPTURE_HEADINGS: Partial<Record<LinkVerdict, string>> = {
  gap: "A deed may be missing here",
  broken: "Chain breaks here",
};

/** Said when the engine graded a rupture but had no specific note to add. */
export const RUPTURE_FALLBACK = "Ownership does not carry over between these deeds.";

export function readRuptureHeading(verdict: string | null): string | null {
  if (verdict === null) {
    return null;
  }
  return RUPTURE_HEADINGS[verdict as LinkVerdict] ?? null;
}

/** Whether this hand-off broke the chain, and so needs the fuller treatment. */
export function isRupture(verdict: string | null): boolean {
  return readRuptureHeading(verdict) !== null;
}

/**
 * The question each per-link check answered, in the officer's words. Keyed by the
 * names `LinkChecksDTO.asked()` sends; a question that could not be asked never
 * arrives, so there is no "unknown" wording to choose.
 */
const LINK_CHECK_QUESTIONS: Record<string, string> = {
  identity: "Seller is the previous buyer",
  property: "Same property",
  extent: "Extent within what was acquired",
  recital: "Recites the prior deed",
  dates: "Dates run in order",
};

export function readLinkCheckQuestion(name: string): string {
  return LINK_CHECK_QUESTIONS[name] ?? name;
}

/**
 * What a hand-off that held is called. Said out loud on purpose: a chain that
 * holds should state so, rather than leaving the officer to infer it from the
 * absence of a warning. Silence reads as "not checked", not as "fine".
 */
const JOIN_LABELS: Partial<Record<LinkVerdict, string>> = {
  linked: "ownership carries over",
  weak: "weak link",
};

export function readJoinLabel(verdict: string): string {
  return JOIN_LABELS[verdict as LinkVerdict] ?? verdict;
}

/** How a rupture is named in the summary above the timeline. */
const BANNER_WORDS: Partial<Record<LinkVerdict, string>> = {
  gap: "Deed missing",
  broken: "Chain breaks",
};

export function readBannerWord(verdict: string): string | null {
  return BANNER_WORDS[verdict as LinkVerdict] ?? null;
}

/** Spelled out under a break, where the two names are shown side by side. */
export const SAME_PERSON_LINE =
  "These should be the same person — they do not match.";

/** The first deed in a chain was not handed over by anything; it starts it. */
export const ORIGIN_LABEL = "origin";
