/**
 * The application fields and their grouping, ported from the prototype's
 * `DI.APPLICATION_FIELDS`, so the sidebar labels and order read the same as
 * index.html rather than showing raw backend keys.
 */
export type ApplicationFieldGroup = "Applicant" | "Plot" | "Proposal";

export interface ApplicationFieldSpec {
  key: string;
  label: string;
  group: ApplicationFieldGroup;
  /** A date value is formatted; an id value is monospaced; aadhaar is masked. */
  kind?: "date" | "id";
  mask?: boolean;
}

export const APPLICATION_FIELDS: ApplicationFieldSpec[] = [
  { key: "applicantName", label: "Applicant", group: "Applicant" },
  { key: "parentName", label: "Father or husband", group: "Applicant" },
  { key: "dob", label: "Date of birth", group: "Applicant", kind: "date" },
  { key: "gender", label: "Gender", group: "Applicant" },
  { key: "aadhaarNo", label: "Aadhaar", group: "Applicant", kind: "id", mask: true },
  // Masked in DI though the prototype shows it plain: this pane renders a real
  // applicant's PII, and a PAN does not need to be on screen to scrutinise against.
  { key: "pan", label: "PAN", group: "Applicant", kind: "id", mask: true },
  { key: "mobile", label: "Mobile", group: "Applicant", kind: "id" },
  { key: "address", label: "Address", group: "Applicant" },
  { key: "plotNo", label: "Plot number", group: "Plot", kind: "id" },
  { key: "surveyNo", label: "Survey number", group: "Plot", kind: "id" },
  { key: "village", label: "Village", group: "Plot" },
  { key: "mandal", label: "Mandal", group: "Plot" },
  { key: "district", label: "District", group: "Plot" },
  { key: "ulb", label: "Urban local body", group: "Plot" },
  { key: "extentSqYd", label: "Extent (sq. yd)", group: "Plot" },
  { key: "proposedUse", label: "Proposed use", group: "Proposal" },
  { key: "floors", label: "Floors", group: "Proposal" },
  { key: "heightM", label: "Height (m)", group: "Proposal" },
  { key: "nearWaterBody", label: "Near water body", group: "Proposal" },
  { key: "roadWidthM", label: "Road width (m)", group: "Proposal" },
];

export const APPLICATION_FIELD_GROUPS: ApplicationFieldGroup[] = [
  "Applicant",
  "Plot",
  "Proposal",
];

const NOT_SET = "Not set";

/** dd Mon yyyy, the prototype's date form; falls back to the raw value. */
export function formatApplicationDate(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

const AADHAAR_DIGITS = 12;
const VISIBLE_TAIL = 4;

/**
 * Hides an identifier down to its last four characters, so a real PAN or Aadhaar
 * never sits in full on the officer's screen. Aadhaar keeps the prototype's
 * grouped form; anything else is masked with a leading run of X.
 */
export function maskIdentifier(value: string): string {
  const trimmed = value.trim();
  const digits = trimmed.replace(/\D/g, "");
  if (digits.length === AADHAAR_DIGITS) {
    return `XXXX XXXX ${digits.slice(-VISIBLE_TAIL)}`;
  }
  if (trimmed.length <= VISIBLE_TAIL) {
    return trimmed;
  }
  const masked = "X".repeat(trimmed.length - VISIBLE_TAIL);
  return `${masked}${trimmed.slice(-VISIBLE_TAIL)}`;
}

export function readFieldDisplay(
  spec: ApplicationFieldSpec,
  raw: string | undefined,
): { text: string; empty: boolean } {
  if (raw === undefined || raw === null || raw === "") {
    return { text: NOT_SET, empty: true };
  }
  if (spec.kind === "date") {
    return { text: formatApplicationDate(raw), empty: false };
  }
  if (spec.mask) {
    return { text: maskIdentifier(raw), empty: false };
  }
  return { text: raw, empty: false };
}
