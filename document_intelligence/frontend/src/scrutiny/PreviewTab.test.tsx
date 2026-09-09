import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { buildDocument } from "@/test/factories";
import { PreviewTab } from "./PreviewTab";

function fields(values: Record<string, string>) {
  return Object.entries(values).map(([key, value]) => ({
    key,
    value,
    confidence: 0.97,
    edited: false,
    confirmed: false,
  }));
}

describe("the document preview", () => {
  it("draws an Aadhaar as its card, with the values it read", () => {
    const { container } = render(
      <PreviewTab
        document={buildDocument({
          documentTypeId: "aadhaar",
          documentTypeLabel: "Aadhaar",
          fieldValues: fields({
            name: "Srinivas Rao Kandula",
            dob: "1979-08-14",
            gender: "Male",
            aadhaarNo: "7316 5520 4821",
            address: "Plot 42, Bachupally",
          }),
          structureFindings: { photo: true, qr: true },
        })}
      />,
    );

    // The issuing authority the prototype prints on the card.
    expect(screen.getByText("Unique Identification Authority")).toBeInTheDocument();
    expect(screen.getByText("Srinivas Rao Kandula")).toBeInTheDocument();
    // The identifier gets the wide, spaced-out treatment.
    expect(screen.getByText("7316 5520 4821")).toBeInTheDocument();
    expect(container.querySelector(".pv-card-aadhaar")).not.toBeNull();
    expect(container.querySelector(".pv-bigid")).not.toBeNull();
  });

  it("labels each drawn value and marks which field it came from", () => {
    const { container } = render(
      <PreviewTab
        document={buildDocument({
          documentTypeId: "aadhaar",
          fieldValues: fields({ name: "Srinivas Rao Kandula" }),
          structureFindings: {},
        })}
      />,
    );

    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(container.querySelector('[data-hl="name"]')).not.toBeNull();
  });

  it("draws a PAN with its own title and band", () => {
    const { container } = render(
      <PreviewTab
        document={buildDocument({
          documentTypeId: "pan",
          documentTypeLabel: "PAN",
          fieldValues: fields({ name: "MOHAMMED IRFAN", pan: "BNMPS7720K" }),
          structureFindings: { photo: true, signature: true },
        })}
      />,
    );

    expect(screen.getByText("Income Tax Department")).toBeInTheDocument();
    // Printed as the card's title, and again as the label on the wide id row.
    expect(screen.getAllByText("Permanent Account Number")).toHaveLength(2);
    expect(container.querySelector(".pv-card-pan")).not.toBeNull();
    // A signature was found, so the line is drawn.
    expect(screen.getByText("Signature")).toBeInTheDocument();
  });

  it("draws a sale deed as a stamped page that recites what was read", () => {
    render(
      <PreviewTab
        document={buildDocument({
          documentTypeId: "sale_deed",
          documentTypeLabel: "Sale deed",
          fieldValues: fields({
            docNo: "5820/2019",
            sro: "Serilingampally",
            vendor: "Sunita Sharma",
            purchaser: "Prakash Iyer",
            plotNo: "17",
            surveyNo: "142/2",
            extent: "400 Sq. Yards",
            village: "Kondapur",
          }),
          structureFindings: {},
        })}
      />,
    );

    expect(screen.getByText("SALE DEED")).toBeInTheDocument();
    expect(screen.getByText("Non-judicial stamp paper")).toBeInTheDocument();
    expect(screen.getByText("Schedule of property")).toBeInTheDocument();
    expect(screen.getByText("Sunita Sharma")).toBeInTheDocument();
    expect(screen.getByText("Prakash Iyer")).toBeInTheDocument();
  });

  it("titles a link document as one", () => {
    render(
      <PreviewTab
        document={buildDocument({
          documentTypeId: "link_doc",
          documentTypeLabel: "Link document",
          fieldValues: fields({ docNo: "2451/2011" }),
          structureFindings: {},
        })}
      />,
    );

    expect(screen.getByText("LINK DOCUMENT")).toBeInTheDocument();
  });

  it("does not draw a template element the read reported absent", () => {
    const { container } = render(
      <PreviewTab
        document={buildDocument({
          documentTypeId: "pan",
          fieldValues: fields({ name: "MOHAMMED IRFAN" }),
          // The signature was looked for and not found.
          structureFindings: { photo: true, signature: false },
        })}
      />,
    );

    expect(screen.queryByText("Signature")).not.toBeInTheDocument();
    // And it is reported honestly in the security chips instead.
    expect(screen.getByText(/signature not found/i)).toBeInTheDocument();
    expect(container.querySelector(".pv-photo")).not.toBeNull();
  });

  it("prefers a real page image over any redrawing of it", () => {
    render(
      <PreviewTab
        document={buildDocument({
          documentTypeId: "aadhaar",
          filename: "aadhaar_front.jpg",
          fieldValues: fields({ name: "Srinivas Rao Kandula" }),
          pageImageUrls: ["/uploads/aadhaar_front.jpg"],
        })}
      />,
    );

    expect(
      screen.getByRole("img", { name: /aadhaar_front\.jpg, page 1/i }),
    ).toBeInTheDocument();
    // The drawn card is not used when the real thing is held.
    expect(screen.queryByText("Unique Identification Authority")).not.toBeInTheDocument();
  });

  it("falls back to a placeholder when nothing has been read", () => {
    render(
      <PreviewTab
        document={buildDocument({
          documentTypeId: null,
          filename: "New Addhar.jpeg",
          fieldValues: [],
          structureFindings: {},
        })}
      />,
    );

    // Named on the placeholder as well as in the File fact above it.
    expect(screen.getAllByText("New Addhar.jpeg").length).toBeGreaterThan(1);
    expect(screen.getByText(/no page image is held/i)).toBeInTheDocument();
  });

  it("still states the file's own facts alongside the drawing", () => {
    render(
      <PreviewTab
        document={buildDocument({
          documentTypeId: "aadhaar",
          filename: "aadhaar_front.jpg",
          fileFormat: "JPG",
          pageCount: 2,
          fieldValues: fields({ name: "Srinivas Rao Kandula" }),
        })}
      />,
    );

    expect(screen.getByText("Format")).toBeInTheDocument();
    expect(screen.getByText("JPG")).toBeInTheDocument();
    expect(screen.getByText("Pages")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
