import type {
  Check,
  CheckStatus,
  DocumentState,
  FieldValue,
  Party,
} from "@/api/contracts";

const BYTES_PER_KILOBYTE = 1024;
const LOW_CONFIDENCE_FLOOR = 0.9;

const FIELD_LABELS: Record<string, string> = {
  name: "Name",
  parentName: "Father's name",
  dob: "Date of birth",
  pan: "PAN",
  aadhaarNo: "Aadhaar",
  gender: "Gender",
  address: "Address",
  dlNo: "Licence number",
  validUpto: "Valid until",
  bloodGroup: "Blood group",
  docNo: "Document number",
  regDate: "Registration date",
  sro: "Sub-registrar office",
  vendor: "Vendor",
  purchaser: "Purchaser",
  surveyNo: "Survey number",
  plotNo: "Plot number",
  extent: "Extent",
  village: "Village",
  consideration: "Consideration",
  boundaries: "Boundaries",
  nocNo: "NOC number",
  issuedBy: "Issued by",
  issueDate: "Issue date",
  applicant: "Applicant",
  bufferCondition: "Buffer condition",
  // Encumbrance certificate
  ecNo: "EC number",
  period: "Period searched",
  owner: "Owner on record",
  encumbrances: "Encumbrances found",
  // Land conversion certificate
  conversionOrderNo: "Conversion order number",
  convertedUse: "Converted use",
  nalaAssessment: "NALA assessment paid",
  // Market value certificate
  certificateNo: "Certificate number",
  marketValuePerSqYd: "Market value per sq. yd",
  valuationAsOn: "Valuation as on",
  // Pattadar pass book / title deed
  passbookNo: "Pass book number",
  pattadar: "Pattadar",
  khataNo: "Khata number",
  landClassification: "Land classification",
  // Occupancy rights certificate
  orcNo: "ORC number",
  occupant: "Occupant",
  inamCategory: "Inam category",
};

export function readFieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

const FIRST_PAGE_NUMBER = 1;

/**
 * The pages a document occupies inside a bundle, counted the way an officer
 * counts them — from one. Null for a document that is a whole file of its own.
 */
export function readPageRange(document: DocumentState): string | null {
  if (document.pageStart === null || document.pageEnd === null) {
    return null;
  }
  const first = document.pageStart + FIRST_PAGE_NUMBER;
  const last = document.pageEnd + FIRST_PAGE_NUMBER;
  return first === last ? `p. ${first}` : `pp. ${first}–${last}`;
}

const PARTIES_SHOWN = 2;
export const NO_PARTY_NAMED = "unknown";

export interface NamedParty {
  /** The name, with a differently transliterated original in brackets after it. */
  text: string;
  /** How many further parties were not named, for a joint-family list. */
  othersCount: number;
}

/**
 * Who a deed names, short enough to sit on one line. A joint family can run to a
 * dozen names; showing them all would swallow the timeline, so the first two are
 * named and the rest are counted.
 *
 * A name the deed spelled differently from the chain's own reading is kept in
 * brackets rather than dropped: the difference is the very thing an officer is
 * being asked to accept or reject.
 */
export function readPartyNames(
  parties: Party[],
  max: number = PARTIES_SHOWN,
): NamedParty {
  if (parties.length === 0) {
    return { text: NO_PARTY_NAMED, othersCount: 0 };
  }
  const text = parties
    .slice(0, max)
    .map((party) =>
      party.nameOriginal === null || party.nameOriginal === party.name
        ? party.name
        : `${party.name} (${party.nameOriginal})`,
    )
    .join(", ");
  return { text, othersCount: Math.max(parties.length - max, 0) };
}

export function formatFileSize(bytes: number): string {
  if (bytes < BYTES_PER_KILOBYTE) {
    return `${bytes} B`;
  }
  const kilobytes = bytes / BYTES_PER_KILOBYTE;
  if (kilobytes < BYTES_PER_KILOBYTE) {
    return `${Math.round(kilobytes)} KB`;
  }
  return `${(kilobytes / BYTES_PER_KILOBYTE).toFixed(1)} MB`;
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/** Worth the officer's eye even when the value happens to match. */
export function isLowConfidence(field: FieldValue): boolean {
  return !field.edited && field.confidence < LOW_CONFIDENCE_FLOOR;
}

/** A check still waiting on the officer, matching the backend's own rule. */
export function isOpenCheck(check: Check): boolean {
  const disagrees =
    check.status === "fail" ||
    check.status === "warn" ||
    check.status === "unavailable";
  return disagrees && !check.acknowledged && !check.manual;
}

export function countOpenChecks(document: DocumentState): number {
  return document.checks.filter(isOpenCheck).length;
}

/** Worst first: a disagreement outranks an unreachable department, and so on. */
const SEVERITY_ORDER: CheckStatus[] = ["fail", "unavailable", "warn", "info"];

/**
 * The gravest status among the checks still waiting on the officer, so a count can
 * be coloured by what it actually holds. One outstanding disagreement and one
 * outstanding note are both "1 open", and an officer needs to tell them apart
 * without opening the tab.
 */
export function readWorstOpenStatus(document: DocumentState): CheckStatus | null {
  const open = document.checks.filter(isOpenCheck);
  for (const status of SEVERITY_ORDER) {
    if (open.some((check) => check.status === status)) {
      return status;
    }
  }
  return null;
}

export function isBeingRead(document: DocumentState): boolean {
  return document.stage !== "queued" && document.stage !== "done";
}

/** Only the issuer's own answer can be re-asked, and only if it did not agree. */
export function findRetryableIssuerCheck(document: DocumentState): Check | null {
  const issuer = document.checks.find((check) => check.group === "external");
  if (issuer === undefined || issuer.status === "pass") {
    return null;
  }
  // No call was made, so there is nothing to repeat: this document's department
  // publishes no interface. Offering "ask again" here would promise something the
  // server would refuse.
  if (issuer.issuerCall === null) {
    return null;
  }
  return issuer;
}

/**
 * A check the officer can only close by verifying the document themselves.
 *
 * The department's answer stands in for a check no machine can settle: when there
 * is no interface to ask, nothing will ever change the verdict, and neither
 * accepting it nor asking the applicant is the remedy. So the one action offered is
 * the one that applies. It is deliberately not folded into `isOpenCheck` — this is
 * not an item held against the application, and counting it as open would put an
 * unclosable entry in the officer's queue.
 */
export function offersOnlyManualVerification(check: Check): boolean {
  return (
    check.group === "external" &&
    check.status === "info" &&
    check.issuerCall === null &&
    !check.manual
  );
}
