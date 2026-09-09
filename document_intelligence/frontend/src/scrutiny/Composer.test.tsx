import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { scrutinyApi } from "@/api/scrutinyApi";
import { ApiError } from "@/api/apiError";
import {
  buildApplication,
  buildDocument,
  buildSummary,
  MISMATCH_APPLICATION_ID,
} from "@/test/factories";
import { DONE_FRAME, stubEventStream, summaryFrame } from "@/test/fakeStream";
import { takeUpApplication } from "@/test/takeUpApplication";
import { WorkspaceShell } from "./WorkspaceShell";

const THREAD_ID = "thread_abc";

function file(name: string) {
  return new File(["x"], name, { type: "image/jpeg" });
}

async function openThread() {
  vi.spyOn(scrutinyApi, "getApplications").mockResolvedValue([buildApplication()]);
  vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
    threadId: THREAD_ID,
    applicationId: MISMATCH_APPLICATION_ID,
    serviceOverrides: {},
    documents: [],
  });

  render(<WorkspaceShell />);
  await takeUpApplication(MISMATCH_APPLICATION_ID);
}

function fileInput() {
  return screen.getByLabelText(/documents to attach/i);
}

function tray() {
  return screen.getByRole("list", { name: /documents ready to verify/i });
}

describe("the composer", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("sits below the scrolling document area, so it stays put", async () => {
    await openThread();

    const composer = screen.getByRole("contentinfo");
    const scroller = composer.previousElementSibling;

    // Pinned means: a sibling AFTER the scroll area, not a child of it.
    expect(scroller?.tagName).toBe("SECTION");
    expect(scroller?.className).toContain("overflow-y-auto");
    expect(scroller?.contains(composer)).toBe(false);
  });

  it("stages an attached file without uploading it", async () => {
    await openThread();
    const upload = vi.spyOn(scrutinyApi, "addDocuments");

    await userEvent.upload(fileInput(), file("pan_card.jpg"));

    expect(within(tray()).getByText("pan_card.jpg")).toBeInTheDocument();
    expect(upload).not.toHaveBeenCalled();
  });

  it("cannot verify until something is attached", async () => {
    await openThread();

    expect(screen.getByRole("button", { name: /^verify$/i })).toBeDisabled();

    await userEvent.upload(fileInput(), file("pan_card.jpg"));

    expect(screen.getByRole("button", { name: /^verify$/i })).toBeEnabled();
  });

  it("lets a wrong pick be taken off the tray before it is ever sent", async () => {
    await openThread();
    const upload = vi.spyOn(scrutinyApi, "addDocuments");
    await userEvent.upload(fileInput(), [file("right.jpg"), file("wrong.jpg")]);

    await userEvent.click(screen.getByRole("button", { name: /remove wrong\.jpg/i }));

    expect(within(tray()).getByText("right.jpg")).toBeInTheDocument();
    expect(within(tray()).queryByText("wrong.jpg")).not.toBeInTheDocument();
    expect(upload).not.toHaveBeenCalled();
  });

  it("sends only what is left on the tray, in one press", async () => {
    await openThread();
    const upload = vi
      .spyOn(scrutinyApi, "addDocuments")
      .mockResolvedValue([buildDocument({ stage: "queued" })]);
    stubEventStream([summaryFrame(buildSummary()), DONE_FRAME]);
    await userEvent.upload(fileInput(), [file("right.jpg"), file("wrong.jpg")]);
    await userEvent.click(screen.getByRole("button", { name: /remove wrong\.jpg/i }));

    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));

    await waitFor(() => expect(upload).toHaveBeenCalledTimes(1));
    const [, sent] = upload.mock.calls[0];
    expect(sent.map((each: File) => each.name)).toEqual(["right.jpg"]);
  });

  it("clears the tray once the upload is accepted", async () => {
    await openThread();
    vi.spyOn(scrutinyApi, "addDocuments").mockResolvedValue([
      buildDocument({ stage: "queued" }),
    ]);
    stubEventStream([summaryFrame(buildSummary()), DONE_FRAME]);
    await userEvent.upload(fileInput(), file("pan_card.jpg"));

    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));

    await waitFor(() =>
      expect(
        screen.queryByRole("list", { name: /documents ready to verify/i }),
      ).not.toBeInTheDocument(),
    );
  });

  it("keeps a rejected batch on the tray so the officer can fix it", async () => {
    await openThread();
    vi.spyOn(scrutinyApi, "addDocuments").mockRejectedValue(
      new ApiError({
        status: 400,
        errorCode: "too_large",
        detail: {
          filename: "huge.jpg",
          message: "huge.jpg is larger than the upload limit.",
        },
      }),
    );
    await userEvent.upload(fileInput(), file("huge.jpg"));

    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /larger than the upload limit/i,
    );
    expect(within(tray()).getByText("huge.jpg")).toBeInTheDocument();
  });

  it("only offers the picker the formats the backend accepts", async () => {
    await openThread();

    // The guard rejects anything else server-side too; this keeps the officer
    // from picking a file that was never going to be read.
    expect(fileInput()).toHaveAttribute("accept", ".pdf,.jpg,.jpeg,.png");
  });

  it("does not start a run when the upload was refused", async () => {
    await openThread();
    vi.spyOn(scrutinyApi, "addDocuments").mockRejectedValue(
      new ApiError({ status: 400, errorCode: "too_large", detail: {} }),
    );
    const stream = stubEventStream([DONE_FRAME]);
    await userEvent.upload(fileInput(), file("huge.jpg"));

    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));

    await screen.findByRole("alert");
    const analyzeCalls = stream.mock.calls.filter(([url]) =>
      String(url).includes("/analyze"),
    );
    expect(analyzeCalls).toHaveLength(0);
  });

  it("can verify documents already attached, with nothing new on the tray", async () => {
    await openThread();
    vi.spyOn(scrutinyApi, "addDocuments").mockResolvedValue([
      buildDocument({ stage: "queued" }),
    ]);
    stubEventStream([summaryFrame(buildSummary()), DONE_FRAME]);
    await userEvent.upload(fileInput(), file("pan_card.jpg"));
    await userEvent.click(screen.getByRole("button", { name: /^verify$/i }));
    await waitFor(() =>
      expect(
        screen.queryByRole("list", { name: /documents ready to verify/i }),
      ).not.toBeInTheDocument(),
    );

    // The document came back still queued, so there is work left to do.
    expect(screen.getByRole("button", { name: /^verify$/i })).toBeEnabled();
  });

  it("shows every document waiting on the tray", async () => {
    await openThread();

    await userEvent.upload(fileInput(), [file("one.jpg"), file("two.jpg")]);

    const waiting = tray();
    expect(within(waiting).getByText("one.jpg")).toBeInTheDocument();
    expect(within(waiting).getByText("two.jpg")).toBeInTheDocument();
  });

  it("is not offered before an application is chosen", async () => {
    vi.spyOn(scrutinyApi, "getApplications").mockResolvedValue([buildApplication()]);

    render(<WorkspaceShell />);
    await screen.findByRole("button", { name: /new scrutiny/i });

    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("carries the prototype's message field", async () => {
    await openThread();

    expect(
      screen.getByRole("textbox", { name: /message/i }),
    ).toHaveAttribute("placeholder", "Ask about the documents, or attach files");
  });

  it("verifies the staged documents when the arrow is pressed", async () => {
    await openThread();
    const upload = vi
      .spyOn(scrutinyApi, "addDocuments")
      .mockResolvedValue([buildDocument({ stage: "queued" })]);
    stubEventStream([summaryFrame(buildSummary()), DONE_FRAME]);
    await userEvent.upload(fileInput(), file("pan_card.jpg"));

    // The dark arrow button carries the Verify action.
    await userEvent.click(screen.getByRole("button", { name: /verify/i }));

    // The upload is sent — proof the arrow triggers the run, not chat.
    await waitFor(() => expect(upload).toHaveBeenCalled());
  });
});

describe("dropping documents", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("invites a drop anywhere in the workspace", async () => {
    await openThread();
    const main = screen.getByRole("main");

    fireDragEnter(main, [file("pan_card.jpg")]);

    expect(
      await screen.findByText(/drop documents to add them to this scrutiny/i),
    ).toBeInTheDocument();
  });

  it("stages what was dropped", async () => {
    await openThread();
    const main = screen.getByRole("main");
    const dropped = file("pan_card.jpg");

    fireDragEnter(main, [dropped]);
    fireDrop(main, [dropped]);

    expect(within(tray()).getByText("pan_card.jpg")).toBeInTheDocument();
  });

  it("stops inviting once the drag leaves", async () => {
    await openThread();
    const main = screen.getByRole("main");

    fireDragEnter(main, [file("pan_card.jpg")]);
    fireDragLeave(main);

    await waitFor(() =>
      expect(
        screen.queryByText(/drop documents to add them/i),
      ).not.toBeInTheDocument(),
    );
  });
});

function dataTransfer(files: File[]) {
  return { files, items: files.map(() => ({ kind: "file" })), types: ["Files"] };
}

function fireDragEnter(target: Element, files: File[]) {
  fireEvent.dragEnter(target, { dataTransfer: dataTransfer(files) });
}

function fireDragLeave(target: Element) {
  fireEvent.dragLeave(target, { dataTransfer: dataTransfer([]) });
}

function fireDrop(target: Element, files: File[]) {
  fireEvent.drop(target, { dataTransfer: dataTransfer(files) });
}
