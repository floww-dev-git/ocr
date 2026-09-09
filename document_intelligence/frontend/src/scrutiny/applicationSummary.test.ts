import { describe, expect, it } from "vitest";

import {
  matchesApplicationSearch,
  readApplicationHeadline,
} from "./applicationSummary";
import { buildApplication } from "@/test/factories";

describe("readApplicationHeadline", () => {
  it("leads with the applicant, because that is what an officer recognises", () => {
    const headline = readApplicationHeadline(buildApplication());

    expect(headline.applicantName).toBe("Mohammed Irfan Siddiqui");
    expect(headline.applicationId).toBe("BN/2026/0377");
  });

  it("says the applicant is not named rather than showing a blank line", () => {
    const headline = readApplicationHeadline(
      buildApplication({ fieldValues: {} }),
    );

    expect(headline.applicantName).toBe("Applicant not named");
  });

  it("joins the use and the village into one readable place", () => {
    expect(readApplicationHeadline(buildApplication()).place).toBe(
      "Commercial, Kokapet",
    );
  });

  it("omits the separator when only one part of the place is known", () => {
    const headline = readApplicationHeadline(
      buildApplication({ fieldValues: { village: "Kokapet" } }),
    );

    expect(headline.place).toBe("Kokapet");
  });
});

describe("matchesApplicationSearch", () => {
  const application = buildApplication();

  it("matches nothing typed at all", () => {
    expect(matchesApplicationSearch(application, "")).toBe(true);
    expect(matchesApplicationSearch(application, "   ")).toBe(true);
  });

  it("matches on the application number an officer would quote", () => {
    expect(matchesApplicationSearch(application, "0377")).toBe(true);
  });

  it("matches on the applicant's name, ignoring case", () => {
    expect(matchesApplicationSearch(application, "siddiqui")).toBe(true);
  });

  it("matches on the village", () => {
    expect(matchesApplicationSearch(application, "kokapet")).toBe(true);
  });

  it("does not match something absent from all three", () => {
    expect(matchesApplicationSearch(application, "bachupally")).toBe(false);
  });
});
