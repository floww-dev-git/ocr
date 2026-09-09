import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { buildApplication, buildDocument, buildSummary } from "@/test/factories";
import { DetailsSidebar } from "./DetailsSidebar";

describe("the details sidebar", () => {
  it("labels application fields the way the prototype does, not by raw key", () => {
    render(
      <DetailsSidebar
        application={buildApplication({
          fieldValues: { applicantName: "Prakash Iyer", ulb: "GHMC" },
        })}
        summary={null}
        documents={[]}
      />,
    );

    const panel = screen.getByRole("complementary", { name: /application details/i });
    // "Urban local body", not "ulb".
    expect(panel).toHaveTextContent("Urban local body");
    expect(panel).toHaveTextContent("Applicant");
    expect(panel).not.toHaveTextContent("applicantName");
  });

  it("groups the fields under Applicant, Plot and Proposal", () => {
    render(
      <DetailsSidebar application={buildApplication()} summary={null} documents={[]} />,
    );

    const panel = screen.getByRole("complementary", { name: /application details/i });
    expect(panel).toHaveTextContent("Applicant");
    expect(panel).toHaveTextContent("Plot");
    expect(panel).toHaveTextContent("Proposal");
  });

  it("shows an italic placeholder for a field the application leaves blank", () => {
    render(
      <DetailsSidebar
        application={buildApplication({ fieldValues: { applicantName: "Prakash Iyer" } })}
        summary={null}
        documents={[]}
      />,
    );

    // Mandal was not provided, so it reads "Not set".
    expect(
      screen.getByRole("complementary", { name: /application details/i }),
    ).toHaveTextContent("Not set");
  });

  it("keeps the applicant's PAN and Aadhaar out of the panel in full", () => {
    render(
      <DetailsSidebar
        application={buildApplication({
          fieldValues: { pan: "BNMPS7720K", aadhaarNo: "551809326604" },
        })}
        summary={null}
        documents={[]}
      />,
    );

    const panel = screen.getByRole("complementary", { name: /application details/i });
    expect(panel).not.toHaveTextContent("BNMPS7720K");
    expect(panel).not.toHaveTextContent("551809326604");
    // The last four still show, so the officer can still tell them apart.
    expect(panel).toHaveTextContent("720K");
    expect(panel).toHaveTextContent("6604");
  });

  it("shows the required-documents checklist before anything is attached", () => {
    render(
      <DetailsSidebar
        application={buildApplication({
          fieldValues: { heightM: "14.8", nearWaterBody: "Yes" },
        })}
        summary={buildSummary({ documentCount: 0 })}
        documents={[]}
      />,
    );

    const checklist = screen.getByRole("list", {
      name: /documents under scrutiny/i,
    });
    // The five required documents for a near-water-body application, all Missing.
    for (const label of ["Aadhaar", "PAN", "Sale deed", "Link document", "Irrigation NOC"]) {
      expect(within(checklist).getByText(label)).toBeInTheDocument();
    }
    expect(within(checklist).getAllByText("Missing")).toHaveLength(5);
    // The six supported optional documents.
    for (const label of [
      "Driving licence",
      "Encumbrance certificate",
      "Land conversion certificate",
      "Market value certificate",
      "Pattadar pass book / Title deed",
      "Occupancy rights certificate",
    ]) {
      expect(within(checklist).getByText(label)).toBeInTheDocument();
    }
    expect(within(checklist).getAllByText("Optional")).toHaveLength(6);
    // The header counts the required set only.
    expect(
      screen.getByRole("button", { name: /collapse the documents list/i }),
    ).toHaveTextContent("0 of 5 required");
  });

  it("flips a required row to Provided once its document is verified", () => {
    render(
      <DetailsSidebar
        application={buildApplication({
          fieldValues: { heightM: "14.8", nearWaterBody: "Yes" },
        })}
        summary={buildSummary()}
        documents={[
          buildDocument({
            documentTypeId: "pan",
            documentTypeLabel: "PAN",
            status: "verified",
            stage: "done",
          }),
        ]}
      />,
    );

    const checklist = screen.getByRole("list", {
      name: /documents under scrutiny/i,
    });
    expect(within(checklist).getByText("Provided")).toBeInTheDocument();
    expect(within(checklist).getAllByText("Missing")).toHaveLength(4);
    expect(
      screen.getByRole("button", { name: /collapse the documents list/i }),
    ).toHaveTextContent("1 of 5 required");
  });

  it("collapses a section when its header is pressed", async () => {
    render(
      <DetailsSidebar application={buildApplication()} summary={null} documents={[]} />,
    );

    expect(screen.getByText("Urban local body")).toBeInTheDocument();
    await userEvent.click(
      screen.getByRole("button", { name: /collapse the application details list/i }),
    );
    expect(screen.queryByText("Urban local body")).not.toBeInTheDocument();
  });

  it("tallies the checks by what each one concluded", () => {
    render(
      <DetailsSidebar
        application={buildApplication()}
        summary={buildSummary({
          statusCounts: { pass: 42, warn: 1, fail: 0, info: 1 },
        })}
        documents={[]}
      />,
    );

    const panel = screen.getByRole("complementary", { name: /application details/i });
    expect(panel).toHaveTextContent("passed");
    expect(panel).toHaveTextContent("warnings");
    expect(panel).toHaveTextContent("failed");
    expect(panel).toHaveTextContent("to note");
    expect(within(panel).getByText("42")).toBeInTheDocument();
  });

  it("counts a status the run never produced as zero rather than omitting it", () => {
    render(
      <DetailsSidebar
        application={buildApplication()}
        summary={buildSummary({ statusCounts: { pass: 9 } })}
        documents={[]}
      />,
    );

    const panel = screen.getByRole("complementary", { name: /application details/i });
    // Three zeroes: warnings, failed, to note. Silence would read as "not checked".
    expect(within(panel).getAllByText("0")).toHaveLength(3);
  });

  it("offers the scrutiny note once something has been read", async () => {
    const onWriteNote = vi.fn();
    render(
      <DetailsSidebar
        application={buildApplication()}
        summary={buildSummary()}
        documents={[]}
        canWriteNote
        onWriteNote={onWriteNote}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /write scrutiny note/i }),
    );

    expect(onWriteNote).toHaveBeenCalledTimes(1);
  });

  it("does not offer the note before anything has been read", () => {
    render(
      <DetailsSidebar
        application={buildApplication()}
        summary={buildSummary()}
        documents={[]}
        canWriteNote={false}
        onWriteNote={() => {}}
      />,
    );

    expect(
      screen.queryByRole("button", { name: /write scrutiny note/i }),
    ).not.toBeInTheDocument();
  });
});
