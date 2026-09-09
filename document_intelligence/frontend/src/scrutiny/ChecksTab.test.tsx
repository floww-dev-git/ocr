import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Check, DocumentState } from "@/api/contracts";
import { buildCheck, buildDocument } from "@/test/factories";
import { ChecksTab } from "./ChecksTab";

const ISSUER_CHECK_ID = "document_1:issuer";

function noInterfaceCheck(overrides: Partial<Check> = {}): Check {
  return buildCheck({
    checkId: ISSUER_CHECK_ID,
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
}

function answeredIssuerCheck(overrides: Partial<Check> = {}): Check {
  return buildCheck({
    checkId: ISSUER_CHECK_ID,
    group: "external",
    status: "unavailable",
    title: "Income Tax PAN verification did not respond",
    detail: "No response after 3000 ms.",
    fieldKey: null,
    issuerCall: {
      issuerServiceId: "itd_pan",
      name: "Income Tax PAN verification",
      endpoint: "POST /pan/verify",
      latencyMs: 3000,
      requestPayload: { pan: "BNMPS7720K" },
      responsePayload: null,
    },
    ...overrides,
  });
}

function renderChecks(document: DocumentState) {
  const onResolveCheck = vi.fn();
  const onRetryVerification = vi.fn();
  render(
    <ChecksTab
      document={document}
      busy={false}
      onResolveCheck={onResolveCheck}
      onRetryVerification={onRetryVerification}
    />,
  );
  return { onResolveCheck, onRetryVerification };
}

describe("a document whose department publishes no interface", () => {
  it("says so, and reads as information rather than a problem", () => {
    renderChecks(buildDocument({ checks: [noInterfaceCheck()] }));

    expect(
      screen.getByText("No department interface for this Irrigation NOC"),
    ).toBeInTheDocument();
    expect(screen.getByText("For information")).toBeInTheDocument();
    expect(screen.queryByText("Needs a look")).not.toBeInTheDocument();
  });

  it("offers the officer the one action that applies", () => {
    const { onResolveCheck } = renderChecks(
      buildDocument({ checks: [noInterfaceCheck()] }),
    );

    expect(
      screen.getByRole("button", { name: "Verified by hand" }),
    ).toBeInTheDocument();
    // Neither of the other two is a remedy: there is nothing to accept and nothing
    // the applicant could send that would change it.
    expect(
      screen.queryByRole("button", { name: "I have seen this" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Ask the applicant" }),
    ).not.toBeInTheDocument();
    expect(onResolveCheck).not.toHaveBeenCalled();
  });

  it("records the officer's verification against the check", async () => {
    const { onResolveCheck } = renderChecks(
      buildDocument({ checks: [noInterfaceCheck()] }),
    );

    await userEvent.click(screen.getByRole("button", { name: "Verified by hand" }));

    expect(onResolveCheck).toHaveBeenCalledWith(ISSUER_CHECK_ID, "manual");
  });

  it("does not offer to ask a department that was never asked", () => {
    renderChecks(buildDocument({ checks: [noInterfaceCheck()] }));

    expect(
      screen.queryByRole("button", { name: /ask the department again/i }),
    ).not.toBeInTheDocument();
  });

  it("has no request and response to disclose", () => {
    renderChecks(buildDocument({ checks: [noInterfaceCheck()] }));

    expect(
      screen.queryByRole("button", { name: /view request and response/i }),
    ).not.toBeInTheDocument();
  });

  it("shows the officer's own verification beside the verdict, not over it", () => {
    renderChecks(buildDocument({ checks: [noInterfaceCheck({ manual: true })] }));

    // The override is stated in its own tag, in the prototype's words.
    expect(screen.getByText("verified manually")).toBeInTheDocument();
    expect(
      screen.getByText("No department interface for this Irrigation NOC"),
    ).toBeInTheDocument();
    // Once recorded there is nothing left to press.
    expect(
      screen.queryByRole("button", { name: "Verified by hand" }),
    ).not.toBeInTheDocument();
  });
});

describe("a document whose department did answer", () => {
  it("can still be asked again", () => {
    renderChecks(buildDocument({ checks: [answeredIssuerCheck()] }));

    expect(
      screen.getByRole("button", { name: /ask the department again/i }),
    ).toBeInTheDocument();
  });

  it("keeps all three dispositions open on an unanswered call", () => {
    renderChecks(buildDocument({ checks: [answeredIssuerCheck()] }));

    expect(screen.getByRole("button", { name: "I have seen this" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verified by hand" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask the applicant" })).toBeInTheDocument();
  });

  it("discloses what was asked and what came back", () => {
    // The prototype's wording, alongside the service and how long it took.
    renderChecks(buildDocument({ checks: [answeredIssuerCheck()] }));

    const disclosure = screen.getByRole("button", {
      name: /view request and response/i,
    });
    expect(disclosure).toBeInTheDocument();
    expect(disclosure).toHaveAttribute("aria-expanded", "false");
  });

  it("names the department, how long it took, and that it is a mock", () => {
    renderChecks(buildDocument({ checks: [answeredIssuerCheck()] }));

    expect(screen.getByText("Income Tax PAN verification")).toBeInTheDocument();
    expect(screen.getByText("3.0 s")).toBeInTheDocument();
    expect(screen.getByText("mock")).toBeInTheDocument();
  });

  it("shows what was sent and received once the disclosure is opened", async () => {
    renderChecks(buildDocument({ checks: [answeredIssuerCheck()] }));

    await userEvent.click(
      screen.getByRole("button", { name: /view request and response/i }),
    );

    expect(screen.getByText(/Sent to/)).toBeInTheDocument();
    expect(screen.getByText("Received")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /hide request and response/i }),
    ).toBeInTheDocument();
  });

  it("groups the checks by the question each one answers", () => {
    renderChecks(
      buildDocument({
        checks: [
          buildCheck({ checkId: "d:name", group: "rule", title: "Name matches" }),
          answeredIssuerCheck(),
        ],
      }),
    );

    expect(
      within(screen.getByRole("list", { name: /rule checks/i })).getByText(
        "Name matches",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("list", { name: /external verification/i }),
    ).toBeInTheDocument();
    // Nothing structural on this document, so that heading is not invented.
    expect(
      screen.queryByRole("list", { name: /security features/i }),
    ).not.toBeInTheDocument();
  });

  it("reads a hand-verified check as settled while still recording the override", () => {
    renderChecks(
      buildDocument({
        checks: [
          buildCheck({
            checkId: "d:issuer",
            group: "external",
            status: "warn",
            title: "Department did not fully match",
            manual: true,
          }),
        ],
      }),
    );

    expect(screen.getByText("verified manually")).toBeInTheDocument();
    // The machine's own verdict is still available to anyone reading by ear.
    expect(screen.getByText("Needs a look")).toBeInTheDocument();
  });
});
