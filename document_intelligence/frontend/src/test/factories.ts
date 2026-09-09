import type {
  Application,
  Check,
  DocumentState,
  OwnershipReport,
  ScrutinySummary,
} from "@/api/contracts";

export const MISMATCH_APPLICATION_ID = "BN/2026/0377";
export const CLEAN_APPLICATION_ID = "BN/2026/0421";

export function buildApplication(overrides: Partial<Application> = {}): Application {
  return {
    applicationId: MISMATCH_APPLICATION_ID,
    status: "Under scrutiny",
    fieldValues: {
      applicantName: "Mohammed Irfan Siddiqui",
      parentName: "Mohammed Yousuf Siddiqui",
      dob: "1982-11-27",
      pan: "BNMPS7720K",
      village: "Kokapet",
      proposedUse: "Commercial",
      floors: "Ground + 3",
      heightM: "14.8",
      surveyNo: "77/2",
      plotNo: "9",
    },
    ...overrides,
  };
}

export function buildCheck(overrides: Partial<Check> = {}): Check {
  return {
    checkId: "document_1:name",
    documentId: "document_1",
    group: "rule",
    title: "Name matches application",
    status: "pass",
    detail: "Everything agrees.",
    fieldKey: "name",
    acknowledged: false,
    manual: false,
    requested: false,
    issuerCall: null,
    ...overrides,
  };
}

export function buildDocument(overrides: Partial<DocumentState> = {}): DocumentState {
  return {
    documentId: "document_1",
    filename: "pan_card.jpg",
    fileFormat: "JPG",
    fileSizeBytes: 188_000,
    documentTypeId: "pan",
    documentTypeLabel: "PAN",
    typeConfidence: 0.99,
    implemented: true,
    stage: "done",
    status: "verified",
    confirmed: false,
    pageCount: 1,
    fieldValues: [],
    structureFindings: {},
    checks: [],
    pageImageUrls: [],
    deedRecord: null,
    parentDocumentId: null,
    pageStart: null,
    pageEnd: null,
    ...overrides,
  };
}

export function buildSummary(
  overrides: Partial<ScrutinySummary> = {},
): ScrutinySummary {
  return {
    threadStatus: "clear",
    documentCount: 1,
    confirmedDocumentCount: 0,
    statusCounts: { pass: 9 },
    openItems: [],
    ...overrides,
  };
}

export function buildOwnershipReport(
  overrides: Partial<OwnershipReport> = {},
): OwnershipReport {
  return {
    threadId: "thread_1",
    verdict: {
      level: "clean",
      headline: "Title traces cleanly from 2003 to today",
      plain: "Ownership flows through 3 registered deeds with no breaks.",
    },
    stats: {
      titleDeedCount: 3,
      spanFrom: "2003",
      spanTo: "2019",
      needReview: 0,
      breaks: 0,
    },
    property: {
      surveyNo: "142/2",
      plotNo: "17",
      extentText: "400 Sq. Yards",
      extentSqYard: 400,
      boundaries: null,
      locality: "Kondapur",
      ulpin: null,
    },
    journey: [],
    authority: [],
    documentsByRole: {},
    attention: [],
    risk: { score: 0, level: "Low", signals: [] },
    chain: {
      overall: "intact",
      counts: { linked: 2 },
      orderedDocumentIds: [],
      excludedDocumentIds: [],
      duplicateDocumentIds: [],
      rolesByDocumentId: {},
      links: [],
      findings: [],
    },
    ...overrides,
  };
}
