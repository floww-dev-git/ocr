/**
 * The wire shapes the backend's presenters emit. These mirror
 * document_scrutiny/presenters/document_presenter.py and are the only place the
 * server's vocabulary is written down on this side.
 */

export const CHECK_STATUSES = [
  "pass",
  "warn",
  "fail",
  "info",
  "pending",
  "unavailable",
] as const;
export type CheckStatus = (typeof CHECK_STATUSES)[number];

export const CHECK_GROUPS = ["rule", "structure", "cross", "external"] as const;
export type CheckGroup = (typeof CHECK_GROUPS)[number];

export const DOCUMENT_STAGES = [
  "queued",
  "identifying",
  "extracting",
  "checking",
  "verifying",
  "done",
] as const;
export type DocumentStage = (typeof DOCUMENT_STAGES)[number];

export const DOCUMENT_STATUSES = [
  "checking",
  "failed",
  "unavailable",
  "attention",
  "verified",
] as const;
export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

export const THREAD_STATUSES = ["new", "running", "attention", "clear"] as const;
export type ThreadStatus = (typeof THREAD_STATUSES)[number];

export const CHECK_RESOLUTIONS = ["acknowledged", "manual", "requested"] as const;
export type CheckResolution = (typeof CHECK_RESOLUTIONS)[number];

export const ANALYSIS_STEPS = ["identify", "extract", "checks", "verify"] as const;
export type AnalysisStep = (typeof ANALYSIS_STEPS)[number];

export type StepState = "running" | "done";

export interface IssuerCall {
  issuerServiceId: string;
  name: string;
  endpoint: string;
  latencyMs: number;
  requestPayload: Record<string, unknown>;
  responsePayload: Record<string, unknown> | null;
}

export interface Check {
  checkId: string;
  documentId: string;
  group: CheckGroup;
  title: string;
  status: CheckStatus;
  detail: string;
  fieldKey: string | null;
  acknowledged: boolean;
  manual: boolean;
  requested: boolean;
  issuerCall: IssuerCall | null;
}

export interface FieldValue {
  key: string;
  value: string;
  confidence: number;
  edited: boolean;
  confirmed: boolean;
}

export interface Party {
  name: string;
  nameOriginal: string | null;
  relation: string | null;
  relativeName: string | null;
  address: string | null;
  pan: string | null;
  aadhaar: string | null;
}
export interface DeedProperty {
  surveyNo: string | null;
  plotNo: string | null;
  extentText: string | null;
  extentSqYard: number | null;
  boundaries: string | null;
  locality: string | null;
  ulpin: string | null;
}
export interface DeedRecord {
  docNo: string | null;
  sro: string | null;
  registrationDate: string | null;
  executionDate: string | null;
  deedType: string | null;
  sellers: Party[];
  buyers: Party[];
  property: DeedProperty;
  considerationText: string | null;
  considerationInr: number | null;
  stampDutyText: string | null;
  estampNo: string | null;
  priorDeedRefs: string[];
  executedViaGpa: boolean;
}
export interface DocumentState {
  documentId: string;
  filename: string;
  fileFormat: string;
  fileSizeBytes: number;
  documentTypeId: string | null;
  documentTypeLabel: string;
  typeConfidence: number;
  implemented: boolean;
  stage: DocumentStage;
  status: DocumentStatus;
  confirmed: boolean;
  pageCount: number;
  fieldValues: FieldValue[];
  structureFindings: Record<string, boolean>;
  checks: Check[];
  pageImageUrls: string[];
  deedRecord: DeedRecord | null;
  /** Set on a document carved out of a bundled file; it is a page range of the parent's. */
  parentDocumentId: string | null;
  pageStart: number | null;
  pageEnd: number | null;
}

export interface OpenItem {
  documentId: string;
  checkId: string;
  text: string;
}

export interface ScrutinySummary {
  threadStatus: ThreadStatus;
  documentCount: number;
  confirmedDocumentCount: number;
  statusCounts: Partial<Record<CheckStatus, number>>;
  openItems: OpenItem[];
}

export interface ScrutinyThread {
  threadId: string;
  applicationId: string;
  serviceOverrides: Record<string, string>;
  documents: DocumentState[];
}

export interface Application {
  applicationId: string;
  status: string;
  fieldValues: Record<string, string>;
}

export interface FieldSpec {
  key: string;
  label: string;
  kind: string;
  applicationFieldKey: string;
  masked: boolean;
  comparisonRule: string;
}

export interface StructureSpec {
  key: string;
  label: string;
}

export interface DocumentType {
  documentTypeId: string;
  label: string;
  icon: string;
  previewLayout: string;
  /** Null for a type whose issuing department publishes no verification interface. */
  issuerServiceId: string | null;
  implemented: boolean;
  fieldSpecs: FieldSpec[];
  structureSpecs: StructureSpec[];
}

export interface IssuerService {
  issuerServiceId: string;
  name: string;
  latencyMs: number;
  endpoint: string;
}

export interface ApplicationFieldSpec {
  key: string;
  label: string;
  kind: string;
  group: string;
  masked: boolean;
  options: string[];
}

export interface DocumentCatalog {
  documentTypes: DocumentType[];
  documentTypeOrder: string[];
  issuerServices: IssuerService[];
  applicationFieldSpecs: ApplicationFieldSpec[];
}

export interface DocumentChange {
  document: DocumentState;
  summary: ScrutinySummary;
  changedCheckIds: string[];
}

export interface CheckChange {
  check: Check;
  document: DocumentState;
  summary: ScrutinySummary;
}

export interface ScrutinyNote {
  threadId: string;
  text: string;
}

/** One Aadhaar demo scenario: a specimen file and what running it demonstrates. */
export interface AadhaarSpecimenScenario {
  id: string;
  filename: string;
  label: string;
  demonstrates: string;
}

/**
 * The chain-of-title report, emitted as one `chain` frame after the summary for
 * any thread holding registered deeds. Mirrors
 * document_scrutiny/presenters/ownership_report_presenter.py.
 *
 * Verdicts and labels arrive as their own vocabulary, never as glyphs: which icon
 * to draw for a break is this side's decision, and a payload carrying one could
 * not be rendered any other way.
 */
export const LINK_VERDICTS = ["linked", "weak", "gap", "broken"] as const;
export type LinkVerdict = (typeof LINK_VERDICTS)[number];
export const CHAIN_VERDICTS = ["intact", "review", "broken"] as const;
export type ChainVerdict = (typeof CHAIN_VERDICTS)[number];
export const REPORT_VERDICT_LEVELS = ["clean", "review", "broken"] as const;
export type ReportVerdictLevel = (typeof REPORT_VERDICT_LEVELS)[number];
export const RISK_LEVELS = ["Low", "Medium", "High"] as const;
export type RiskLevel = (typeof RISK_LEVELS)[number];
export const FINDING_SEVERITIES = ["high", "medium", "low", "clear"] as const;
export type FindingSeverity = (typeof FINDING_SEVERITIES)[number];
export const TITLE_ROLES = ["title", "authority", "metadata"] as const;
export type TitleRole = (typeof TITLE_ROLES)[number];
export type JourneyEntryKind = "owner" | "transfer";

export interface OwnershipParty {
  name: string;
  nameOriginal: string | null;
  relative: string | null;
  othersCount: number;
}
export interface JourneyEntry {
  kind: JourneyEntryKind;
  role: string | null;
  badge: string | null;
  party: OwnershipParty | null;
  meta: string | null;
  isCurrent: boolean;
  verdict: string | null;
  label: string | null;
  reference: string | null;
  note: string | null;
  identityScore: number | null;
}
export interface AttentionItem {
  severity: FindingSeverity;
  verb: string;
  title: string;
  detail: string;
  action: string;
}
export interface RiskSignal {
  severity: FindingSeverity;
  code: string;
  title: string;
  detail: string;
}
export interface RiskAssessment {
  score: number;
  level: RiskLevel;
  signals: RiskSignal[];
}
export interface AuthorityDocument {
  documentId: string;
  deedType: string | null;
  docNo: string | null;
  owner: string;
  holder: string;
}
export interface DocumentRoleRow {
  documentId: string;
  deedType: string | null;
  docNo: string | null;
  date: string | null;
  isRoot: boolean;
}
export interface ChainLink {
  fromDocumentId: string;
  toDocumentId: string;
  fromDocNo: string | null;
  toDocNo: string | null;
  verdict: LinkVerdict;
  identityScore: number;
  /** Only the questions this link could be asked; an unasked check is absent, not false. */
  checks: Partial<Record<string, boolean>>;
  notes: string[];
}
export interface ChainFinding {
  severity: FindingSeverity;
  verdict: string;
  title: string;
  detail: string;
}
export interface ChainOfTitle {
  overall: ChainVerdict;
  counts: Partial<Record<LinkVerdict, number>>;
  orderedDocumentIds: string[];
  excludedDocumentIds: string[];
  duplicateDocumentIds: string[];
  rolesByDocumentId: Record<string, TitleRole>;
  links: ChainLink[];
  findings: ChainFinding[];
}
export interface ReportVerdict {
  level: ReportVerdictLevel;
  headline: string;
  plain: string;
}
export interface ReportStats {
  titleDeedCount: number;
  spanFrom: string | null;
  spanTo: string | null;
  needReview: number;
  breaks: number;
}
export interface OwnershipReport {
  threadId: string;
  verdict: ReportVerdict;
  stats: ReportStats;
  property: DeedProperty;
  journey: JourneyEntry[];
  authority: AuthorityDocument[];
  documentsByRole: Partial<Record<TitleRole, DocumentRoleRow[]>>;
  attention: AttentionItem[];
  risk: RiskAssessment | null;
  chain: ChainOfTitle;
}
/**
 * The SSE frames `GET /api/threads/{id}/analyze` emits. The `event:` line gives
 * the tag; the `data:` line is the payload below, un-nested — a `doc` frame's
 * data IS a DocumentState, not `{document: ...}`.
 */
export interface StepFramePayload {
  step: AnalysisStep;
  state: StepState;
  /** Only present on `checks` completing. */
  count?: number;
}

export interface ErrorFramePayload {
  message: string;
}

export type AnalysisEvent =
  | { type: "step"; payload: StepFramePayload }
  | { type: "doc"; payload: DocumentState }
  | { type: "summary"; payload: ScrutinySummary }
  | { type: "chain"; payload: OwnershipReport }
  | { type: "error"; payload: ErrorFramePayload }
  | { type: "done" };
