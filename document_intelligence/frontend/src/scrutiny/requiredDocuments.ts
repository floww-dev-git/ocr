import type { DocumentState } from "@/api/contracts";
import type { Tone } from "./statusVocabulary";
import { countOpenChecks } from "./documentDisplay";

/**
 * The scrutiny checklist. The Documents panel lists every document type this build
 * can actually read — the supported set — before anything is attached, and each row
 * settles as its document is read.
 *
 * Requiredness follows the prototype's `E.requiredDocs` rule (index.html) for the
 * types it covered: the two identity documents and the two title documents are
 * always required, and the irrigation NOC is required when the plot is near a water
 * body. Every other supported type is optional. The prototype also listed a few
 * types this build does not yet read (fire NOC, AAI NOC, earlier building
 * permission, property tax receipt); those are left off, because the panel shows
 * what the system supports, and the newer land documents it now reads are added.
 *
 * The document type ids and labels are the catalog's own (`link_document`,
 * `driving_licence`, ...). There is no client-side catalog fetch in this build, so
 * the supported set lives here as a small table — the same shape as the field-label
 * map in `documentDisplay.ts` — and must stay in step with the catalog's
 * `implemented=True` types.
 */
export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  aadhaar: "Aadhaar",
  pan: "PAN",
  driving_licence: "Driving licence",
  sale_deed: "Sale deed",
  link_document: "Link document",
  encumbrance_certificate: "Encumbrance certificate",
  conversion_cert: "Land conversion certificate",
  market_value_cert: "Market value certificate",
  pattadar_passbook: "Pattadar pass book / Title deed",
  orc: "Occupancy rights certificate",
  irrigation_noc: "Irrigation NOC",
};

export type ChecklistStatus = "provided" | "review" | "missing" | "optional";

export interface RequiredDoc {
  typeId: string;
  required: boolean;
  reason: string;
}

export interface ChecklistRow {
  typeId: string;
  label: string;
  required: boolean;
  reason: string;
  status: ChecklistStatus;
  reviewCount: number;
  tone: Tone;
}

/**
 * The supported document types this application is expected to carry, and why. The
 * two identity documents and two title documents are always required; the irrigation
 * NOC is required when the plot is near a water body; the rest are optional. Ordered
 * so identity and title lead, then the supporting land records.
 */
export function requiredDocuments(
  fieldValues: Record<string, string>,
): RequiredDoc[] {
  const nearWaterBody = fieldValues.nearWaterBody === "Yes";

  return [
    { typeId: "aadhaar", required: true, reason: "Identity of the applicant" },
    { typeId: "pan", required: true, reason: "Identity of the applicant" },
    { typeId: "sale_deed", required: true, reason: "Title to the plot" },
    { typeId: "link_document", required: true, reason: "Chain of title" },
    {
      typeId: "irrigation_noc",
      required: nearWaterBody,
      reason: nearWaterBody
        ? "Plot is near a water body"
        : "Only for plots near a water body",
    },
    { typeId: "driving_licence", required: false, reason: "Additional identity" },
    {
      typeId: "encumbrance_certificate",
      required: false,
      reason: "Encumbrance history",
    },
    { typeId: "conversion_cert", required: false, reason: "Land-use conversion" },
    { typeId: "market_value_cert", required: false, reason: "Government valuation" },
    { typeId: "pattadar_passbook", required: false, reason: "Revenue title record" },
    { typeId: "orc", required: false, reason: "Occupancy rights (Inam land)" },
  ];
}

function readLabel(typeId: string, documents: DocumentState[]): string {
  const known = DOCUMENT_TYPE_LABELS[typeId];
  if (known !== undefined) {
    return known;
  }
  // A read document of an untabled type still names itself.
  const attached = documents.find((document) => document.documentTypeId === typeId);
  return attached?.documentTypeLabel ?? typeId;
}

function rowFor(entry: RequiredDoc, documents: DocumentState[]): ChecklistRow {
  const settled = documents.filter(
    (document) =>
      document.documentTypeId === entry.typeId && document.stage === "done",
  );
  const base = {
    typeId: entry.typeId,
    label: readLabel(entry.typeId, documents),
    required: entry.required,
    reason: entry.reason,
  };

  if (settled.length > 0) {
    const reviewCount = settled.reduce(
      (total, document) => total + countOpenChecks(document),
      0,
    );
    if (reviewCount > 0) {
      const failed = settled.some((document) => document.status === "failed");
      return {
        ...base,
        status: "review",
        reviewCount,
        tone: failed ? "fail" : "warn",
      };
    }
    return { ...base, status: "provided", reviewCount: 0, tone: "pass" };
  }

  if (entry.required) {
    return { ...base, status: "missing", reviewCount: 0, tone: "fail" };
  }

  return { ...base, status: "optional", reviewCount: 0, tone: "neutral" };
}

/**
 * The rows the Documents panel draws: one for every supported document type, each
 * carrying the status it should read right now. All supported types are shown, so
 * the officer sees the whole set the system can read, attached or not.
 */
export function buildChecklist(
  fieldValues: Record<string, string>,
  documents: DocumentState[],
): ChecklistRow[] {
  return requiredDocuments(fieldValues).map((entry) => rowFor(entry, documents));
}

export interface ChecklistCounts {
  requiredCount: number;
  providedRequiredCount: number;
}

/**
 * The header count, "N of M required": M required for this application, N of those
 * actually provided (a required type is provided once a document of it has settled,
 * whatever its checks say — the same test the prototype's header uses).
 */
export function checklistCounts(
  fieldValues: Record<string, string>,
  documents: DocumentState[],
): ChecklistCounts {
  const providedTypeIds = new Set(
    documents
      .filter((document) => document.stage === "done")
      .map((document) => document.documentTypeId),
  );
  const required = requiredDocuments(fieldValues).filter((entry) => entry.required);
  return {
    requiredCount: required.length,
    providedRequiredCount: required.filter((entry) =>
      providedTypeIds.has(entry.typeId),
    ).length,
  };
}
