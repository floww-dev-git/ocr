import { describe, expect, it } from "vitest";

import { buildCheck, buildDocument } from "@/test/factories";
import {
  buildChecklist,
  checklistCounts,
  requiredDocuments,
} from "./requiredDocuments";

// The seeded near-water-body application: plot by a water body.
const WATER_BODY_FIELDS = { heightM: "14.8", nearWaterBody: "Yes" };
const DRY_PLOT_FIELDS = { heightM: "7", nearWaterBody: "No" };

// Every supported (implemented) type the panel lists, in order.
const SUPPORTED_TYPE_IDS = [
  "aadhaar",
  "pan",
  "sale_deed",
  "link_document",
  "irrigation_noc",
  "driving_licence",
  "encumbrance_certificate",
  "conversion_cert",
  "market_value_cert",
  "pattadar_passbook",
  "orc",
];

function requiredTypeIds(fieldValues: Record<string, string>): string[] {
  return requiredDocuments(fieldValues)
    .filter((entry) => entry.required)
    .map((entry) => entry.typeId);
}

describe("which documents an application must carry", () => {
  it("lists every supported document type, in order", () => {
    expect(requiredDocuments(WATER_BODY_FIELDS).map((entry) => entry.typeId)).toEqual(
      SUPPORTED_TYPE_IDS,
    );
  });

  it("does not list the types this build cannot read", () => {
    const listed = requiredDocuments(WATER_BODY_FIELDS).map((entry) => entry.typeId);
    for (const unsupported of ["fire_noc", "aai_noc", "building_permit", "tax_receipt"]) {
      expect(listed).not.toContain(unsupported);
    }
  });

  it("always requires the two identity documents and the two title documents", () => {
    expect(requiredTypeIds(DRY_PLOT_FIELDS)).toEqual([
      "aadhaar",
      "pan",
      "sale_deed",
      "link_document",
    ]);
  });

  it("requires the irrigation NOC only when the plot is near a water body", () => {
    expect(requiredTypeIds(WATER_BODY_FIELDS)).toContain("irrigation_noc");
    expect(requiredTypeIds(DRY_PLOT_FIELDS)).not.toContain("irrigation_noc");
  });

  it("counts five required for the near-water-body application", () => {
    // aadhaar, pan, sale_deed, link_document, irrigation_noc
    expect(checklistCounts(WATER_BODY_FIELDS, []).requiredCount).toBe(5);
    expect(checklistCounts(WATER_BODY_FIELDS, []).providedRequiredCount).toBe(0);
  });

  it("counts four required for a dry plot (no irrigation NOC needed)", () => {
    expect(checklistCounts(DRY_PLOT_FIELDS, []).requiredCount).toBe(4);
  });

  it("gives the irrigation NOC a reason that explains why it does or does not apply", () => {
    const applies = requiredDocuments(WATER_BODY_FIELDS).find(
      (entry) => entry.typeId === "irrigation_noc",
    );
    const doesNot = requiredDocuments(DRY_PLOT_FIELDS).find(
      (entry) => entry.typeId === "irrigation_noc",
    );
    expect(applies?.reason).toBe("Plot is near a water body");
    expect(doesNot?.reason).toBe("Only for plots near a water body");
  });
});

describe("the checklist rows the panel draws", () => {
  it("marks a required document with nothing attached as Missing", () => {
    const rows = buildChecklist(WATER_BODY_FIELDS, []);
    const pan = rows.find((row) => row.typeId === "pan");
    expect(pan?.status).toBe("missing");
    expect(pan?.tone).toBe("fail");
    expect(pan?.label).toBe("PAN");
  });

  it("draws a row for every supported type, attached or not", () => {
    const rows = buildChecklist(WATER_BODY_FIELDS, []);
    expect(rows.map((row) => row.typeId)).toEqual(SUPPORTED_TYPE_IDS);
  });

  it("shows the five Missing required rows before anything is attached", () => {
    const rows = buildChecklist(WATER_BODY_FIELDS, []);
    const missing = rows.filter((row) => row.status === "missing").map((row) => row.typeId);
    expect(missing).toEqual([
      "aadhaar",
      "pan",
      "sale_deed",
      "link_document",
      "irrigation_noc",
    ]);
  });

  it("shows every supported optional type as Optional before anything is attached", () => {
    const rows = buildChecklist(WATER_BODY_FIELDS, []);
    const optional = rows.filter((row) => row.status === "optional").map((row) => row.typeId);
    expect(optional).toEqual([
      "driving_licence",
      "encumbrance_certificate",
      "conversion_cert",
      "market_value_cert",
      "pattadar_passbook",
      "orc",
    ]);
  });

  it("marks a verified document as Provided", () => {
    const pan = buildDocument({
      documentTypeId: "pan",
      status: "verified",
      stage: "done",
      checks: [buildCheck({ status: "pass" })],
    });
    const rows = buildChecklist(WATER_BODY_FIELDS, [pan]);
    const row = rows.find((entry) => entry.typeId === "pan");
    expect(row?.status).toBe("provided");
    expect(row?.tone).toBe("pass");
    expect(checklistCounts(WATER_BODY_FIELDS, [pan]).providedRequiredCount).toBe(1);
  });

  it("shows a provided document with an open check as 'N to review'", () => {
    const pan = buildDocument({
      documentTypeId: "pan",
      status: "attention",
      stage: "done",
      checks: [buildCheck({ status: "warn" })],
    });
    const rows = buildChecklist(WATER_BODY_FIELDS, [pan]);
    const row = rows.find((entry) => entry.typeId === "pan");
    expect(row?.status).toBe("review");
    expect(row?.reviewCount).toBe(1);
    expect(row?.tone).toBe("warn");
  });

  it("turns the review tone red when the provided document failed", () => {
    const pan = buildDocument({
      documentTypeId: "pan",
      status: "failed",
      stage: "done",
      checks: [buildCheck({ status: "fail" })],
    });
    const row = buildChecklist(WATER_BODY_FIELDS, [pan]).find(
      (entry) => entry.typeId === "pan",
    );
    expect(row?.status).toBe("review");
    expect(row?.tone).toBe("fail");
  });

  it("does not count a still-reading document as provided", () => {
    const reading = buildDocument({
      documentTypeId: "pan",
      stage: "extracting",
      status: "checking",
    });
    const row = buildChecklist(WATER_BODY_FIELDS, [reading]).find(
      (entry) => entry.typeId === "pan",
    );
    expect(row?.status).toBe("missing");
  });
});
