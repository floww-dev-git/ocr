import { describe, expect, it } from "vitest";

import { buildCheck, buildDocument } from "@/test/factories";
import {
  countOpenChecks,
  findRetryableIssuerCheck,
  isOpenCheck,
  offersOnlyManualVerification,
  readFieldLabel,
} from "./documentDisplay";

function buildIssuerCall(overrides = {}) {
  return {
    issuerServiceId: "itd_pan",
    name: "Income Tax PAN verification",
    endpoint: "POST /pan/verify",
    latencyMs: 900,
    requestPayload: { pan: "BNMPS7720K" },
    responsePayload: { status: "VALID" },
    ...overrides,
  };
}

const answeredIssuerCheck = (status: "pass" | "warn" | "fail" | "unavailable") =>
  buildCheck({
    checkId: "document_1:issuer",
    group: "external",
    status,
    issuerCall: buildIssuerCall(),
  });

// What a document whose department publishes no interface carries instead.
const noInterfaceCheck = (overrides = {}) =>
  buildCheck({
    checkId: "document_1:issuer",
    group: "external",
    status: "info",
    title: "No department interface for this Irrigation NOC",
    detail:
      "The department that issues this document does not publish a verification " +
      "interface, so nothing could be asked. Verify it against the original and " +
      "mark it verified by hand.",
    fieldKey: null,
    issuerCall: null,
    ...overrides,
  });

describe("which checks are still waiting on the officer", () => {
  it("counts a disagreement nobody has dealt with", () => {
    expect(isOpenCheck(buildCheck({ status: "warn" }))).toBe(true);
    expect(isOpenCheck(buildCheck({ status: "fail" }))).toBe(true);
    expect(isOpenCheck(buildCheck({ status: "unavailable" }))).toBe(true);
  });

  it("does not count one the officer has already dealt with", () => {
    expect(isOpenCheck(buildCheck({ status: "warn", acknowledged: true }))).toBe(false);
    expect(isOpenCheck(buildCheck({ status: "fail", manual: true }))).toBe(false);
  });

  it("does not hold an absent department against the application", () => {
    // Nothing the applicant can produce would close it, so it is not an open item
    // and it must not sit in the officer's queue as though it were.
    expect(isOpenCheck(noInterfaceCheck())).toBe(false);
    expect(
      countOpenChecks(buildDocument({ checks: [noInterfaceCheck()] })),
    ).toBe(0);
  });
});

describe("offering to ask the department again", () => {
  it("is offered when a department answered and did not agree", () => {
    const document = buildDocument({ checks: [answeredIssuerCheck("unavailable")] });

    expect(findRetryableIssuerCheck(document)?.checkId).toBe("document_1:issuer");
  });

  it("is not offered when the department already agreed", () => {
    const document = buildDocument({ checks: [answeredIssuerCheck("pass")] });

    expect(findRetryableIssuerCheck(document)).toBeNull();
  });

  it("is not offered when no call was ever made", () => {
    // The server would refuse it, so promising it here would be a dead end.
    const document = buildDocument({ checks: [noInterfaceCheck()] });

    expect(findRetryableIssuerCheck(document)).toBeNull();
  });

  it("is not offered to a document that was never verified at all", () => {
    const document = buildDocument({ checks: [buildCheck({ status: "warn" })] });

    expect(findRetryableIssuerCheck(document)).toBeNull();
  });
});

describe("the one action an absent department leaves open", () => {
  it("is offered on an external check that could not be asked", () => {
    expect(offersOnlyManualVerification(noInterfaceCheck())).toBe(true);
  });

  it("stops being offered once the officer has recorded it", () => {
    expect(offersOnlyManualVerification(noInterfaceCheck({ manual: true }))).toBe(false);
  });

  it("is not offered on a department's real answer", () => {
    expect(offersOnlyManualVerification(answeredIssuerCheck("unavailable"))).toBe(false);
    expect(offersOnlyManualVerification(answeredIssuerCheck("pass"))).toBe(false);
  });

  it("is not offered on an informational check from any other group", () => {
    // A bundle's own segmentation notice is `info` too, and re-labelling it as
    // something to verify by hand would be nonsense.
    expect(
      offersOnlyManualVerification(buildCheck({ group: "rule", status: "info" })),
    ).toBe(false);
  });
});

describe("naming what was read", () => {
  it("has words for the fields a clearance letter carries", () => {
    expect(readFieldLabel("nocNo")).toBe("NOC number");
    expect(readFieldLabel("issuedBy")).toBe("Issued by");
    expect(readFieldLabel("issueDate")).toBe("Issue date");
    expect(readFieldLabel("validUpto")).toBe("Valid until");
    expect(readFieldLabel("applicant")).toBe("Applicant");
    expect(readFieldLabel("surveyNo")).toBe("Survey number");
    expect(readFieldLabel("bufferCondition")).toBe("Buffer condition");
  });

  it("has words for the fields the land and revenue documents carry", () => {
    // Encumbrance certificate
    expect(readFieldLabel("ecNo")).toBe("EC number");
    expect(readFieldLabel("encumbrances")).toBe("Encumbrances found");
    // Land conversion certificate
    expect(readFieldLabel("conversionOrderNo")).toBe("Conversion order number");
    expect(readFieldLabel("nalaAssessment")).toBe("NALA assessment paid");
    // Market value certificate
    expect(readFieldLabel("marketValuePerSqYd")).toBe("Market value per sq. yd");
    // Pattadar pass book
    expect(readFieldLabel("pattadar")).toBe("Pattadar");
    expect(readFieldLabel("khataNo")).toBe("Khata number");
    // ORC
    expect(readFieldLabel("orcNo")).toBe("ORC number");
    expect(readFieldLabel("occupant")).toBe("Occupant");
    expect(readFieldLabel("inamCategory")).toBe("Inam category");
  });

  it("falls back to the key rather than showing nothing", () => {
    expect(readFieldLabel("somethingNobodyNamed")).toBe("somethingNobodyNamed");
  });
});
