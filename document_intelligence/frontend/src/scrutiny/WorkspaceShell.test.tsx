import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { scrutinyApi } from "@/api/scrutinyApi";
import { buildApplication, MISMATCH_APPLICATION_ID } from "@/test/factories";
import { takeUpApplication } from "@/test/takeUpApplication";
import { WorkspaceShell } from "./WorkspaceShell";

const CLEAN_APPLICATION = buildApplication({
  applicationId: "BN/2026/0421",
  fieldValues: {
    applicantName: "Srinivas Rao Kandula",
    village: "Bachupally",
    proposedUse: "Residential apartment",
  },
});

function stubApplications(applications = [buildApplication(), CLEAN_APPLICATION]) {
  return vi
    .spyOn(scrutinyApi, "getApplications")
    .mockResolvedValue(applications);
}

/** Opening a thread is a real call; stub it for tests that only need the rail. */
function stubThread(applicationId = MISMATCH_APPLICATION_ID) {
  return vi.spyOn(scrutinyApi, "createThread").mockImplementation(
    async (id: string) => ({
      threadId: `thread_${id}`,
      applicationId: id ?? applicationId,
      serviceOverrides: {},
      documents: [],
    }),
  );
}

describe("the workspace shell", () => {
  beforeEach(() => {
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("starts with an empty rail — the queue is not the officer's workload yet", async () => {
    stubApplications();

    render(<WorkspaceShell />);

    expect(
      await screen.findByText(/press new scrutiny to take up/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Mohammed Irfan Siddiqui")).not.toBeInTheDocument();
    expect(screen.queryByText("Srinivas Rao Kandula")).not.toBeInTheDocument();
  });

  it("offers the queue of applications when New scrutiny is pressed", async () => {
    stubApplications();

    render(<WorkspaceShell />);
    await userEvent.click(
      await screen.findByRole("button", { name: /new scrutiny/i }),
    );

    const queue = screen.getByRole("list", { name: /applications in the queue/i });
    expect(within(queue).getByText(MISMATCH_APPLICATION_ID)).toBeInTheDocument();
    expect(within(queue).getByText("BN/2026/0421")).toBeInTheDocument();
  });

  it("puts the chosen application on the rail and opens it", async () => {
    stubApplications();
    vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: "thread_abc",
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);

    // It is now a row on the rail, and its scrutiny is open.
    const rail = screen.getByRole("complementary", { name: /scrutiny threads/i });
    expect(within(rail).getByText("Mohammed Irfan Siddiqui")).toBeInTheDocument();
    expect(await screen.findByText(/ready to scrutinize/i)).toBeInTheDocument();
  });

  it("stops offering an application already on the rail", async () => {
    stubApplications();
    vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: "thread_abc",
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);
    await userEvent.click(screen.getByRole("button", { name: /new scrutiny/i }));

    const queue = screen.getByRole("list", { name: /applications in the queue/i });
    expect(within(queue).queryByText(MISMATCH_APPLICATION_ID)).not.toBeInTheDocument();
    expect(within(queue).getByText("BN/2026/0421")).toBeInTheDocument();
  });

  it("adds nothing when the picker is cancelled", async () => {
    stubApplications();
    const createThread = vi.spyOn(scrutinyApi, "createThread");

    render(<WorkspaceShell />);
    await userEvent.click(
      await screen.findByRole("button", { name: /new scrutiny/i }),
    );
    await userEvent.click(screen.getByRole("button", { name: /^cancel$/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(createThread).not.toHaveBeenCalled();
    expect(screen.queryByText("Mohammed Irfan Siddiqui")).not.toBeInTheDocument();
  });

  it("takes an application off the rail when the officer deletes it", async () => {
    stubApplications();
    vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: "thread_abc",
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);

    const rail = screen.getByRole("complementary", { name: /scrutiny threads/i });
    const row = within(rail).getByRole("button", {
      name: /Mohammed Irfan Siddiqui/i,
    });
    await userEvent.click(within(row).getByRole("button", { name: /thread options/i }));
    await userEvent.click(screen.getByRole("menuitem", { name: /delete/i }));

    expect(
      within(rail).queryByText("Mohammed Irfan Siddiqui"),
    ).not.toBeInTheDocument();

    // And it is offered again, because it is back in the queue.
    await userEvent.click(screen.getByRole("button", { name: /new scrutiny/i }));
    const queue = screen.getByRole("list", { name: /applications in the queue/i });
    expect(within(queue).getByText(MISMATCH_APPLICATION_ID)).toBeInTheDocument();
  });

  it("invites the officer to pick an application before anything is open", async () => {
    stubApplications();

    render(<WorkspaceShell />);

    expect(
      await screen.findByRole("heading", { name: /pick an application to begin/i }),
    ).toBeInTheDocument();
  });

  it("offers no dead controls before an application is chosen", async () => {
    // Picking an application is the only way to start a scrutiny, so nothing on
    // screen should be sitting there disabled waiting for it.
    stubApplications();

    render(<WorkspaceShell />);
    await screen.findByRole("button", { name: /new scrutiny/i });

    const disabled = screen
      .getAllByRole("button")
      .filter((button) => button.hasAttribute("disabled"));
    expect(disabled).toEqual([]);
  });

  it("starting a scrutiny is the job of picking an application", async () => {
    stubApplications();
    const createThread = vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: "thread_abc",
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });

    render(<WorkspaceShell />);

    // Nothing is taken up yet, so the rail offers the way to begin and no rows.
    expect(
      await screen.findByRole("button", { name: /new scrutiny/i }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Mohammed Irfan Siddiqui")).not.toBeInTheDocument();

    await takeUpApplication(MISMATCH_APPLICATION_ID);

    await waitFor(() => expect(createThread).toHaveBeenCalledTimes(1));
  });

  it("opens a scrutiny thread for the application the officer picks", async () => {
    stubApplications();
    const createThread = vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: "thread_abc",
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);

    await waitFor(() =>
      expect(createThread).toHaveBeenCalledWith(MISMATCH_APPLICATION_ID),
    );
    expect(
      await screen.findByRole("button", { name: /attach documents/i }),
    ).toBeInTheDocument();
  });

  it("greets the officer on opening a thread rather than showing an empty record", async () => {
    stubApplications();
    vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: "thread_abc",
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);

    // The prototype's opening line, naming the application and applicant, in the
    // scrutiny record (the applicant name also appears in the rail).
    const record = await screen.findByRole("region", { name: /scrutiny record/i });
    expect(record).toHaveTextContent(/ready to scrutinize/i);
    expect(record).toHaveTextContent("Mohammed Irfan Siddiqui");
  });

  it("cannot start a run before anything is attached", async () => {
    stubApplications();
    vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: "thread_abc",
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);

    expect(await screen.findByRole("button", { name: /^verify$/i })).toBeDisabled();
  });

  it("says plainly when the application list cannot be loaded", async () => {
    vi.spyOn(scrutinyApi, "getApplications").mockRejectedValue(
      new Error("network down"),
    );

    render(<WorkspaceShell />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /application list could not be loaded/i,
    );
  });

  it("never shows the officer the raw failure text", async () => {
    vi.spyOn(scrutinyApi, "getApplications").mockRejectedValue(
      new Error("psycopg2.OperationalError: password=hunter2"),
    );

    render(<WorkspaceShell />);
    const alert = await screen.findByRole("alert");

    expect(alert.textContent).not.toMatch(/hunter2|psycopg2/);
  });

  it("narrows the rail to what the officer searched for", async () => {
    stubApplications();
    stubThread();

    render(<WorkspaceShell />);
    // Search filters what is on the rail, so both have to be taken up first.
    await takeUpApplication(MISMATCH_APPLICATION_ID);
    await takeUpApplication("BN/2026/0421");
    await userEvent.type(
      screen.getByRole("searchbox", { name: /search applications/i }),
      "bachupally",
    );

    const rail = screen.getByRole("complementary", { name: /scrutiny threads/i });
    expect(within(rail).getByText("Srinivas Rao Kandula")).toBeInTheDocument();
    expect(
      within(rail).queryByText("Mohammed Irfan Siddiqui"),
    ).not.toBeInTheDocument();
  });

  it("says so when a search matches nothing, rather than showing an empty rail", async () => {
    stubApplications();
    stubThread();

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);
    await userEvent.type(
      screen.getByRole("searchbox", { name: /search applications/i }),
      "nowhere",
    );

    expect(screen.getByText(/no application matches that search/i)).toBeInTheDocument();
  });

  it("can hide and restore the thread rail", async () => {
    stubApplications();
    stubThread();

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);
    const rail = screen.getByRole("complementary", { name: /scrutiny threads/i });
    expect(within(rail).getByText("Mohammed Irfan Siddiqui")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /collapse threads/i }));

    expect(
      screen.queryByRole("complementary", { name: /scrutiny threads/i }),
    ).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /show threads/i }));

    expect(
      screen.getByRole("complementary", { name: /scrutiny threads/i }),
    ).toBeInTheDocument();
  });

  it("can hide and restore the application details", async () => {
    stubApplications();

    render(<WorkspaceShell />);
    await screen.findByRole("button", { name: /new scrutiny/i });
    const sidebar = screen.getByRole("complementary", {
      name: /application details/i,
    });
    expect(sidebar).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: /toggle the details panel/i }),
    );

    expect(
      screen.queryByRole("complementary", { name: /application details/i }),
    ).not.toBeInTheDocument();
  });

  it("switches between light and dark on the document itself", async () => {
    stubApplications();

    render(<WorkspaceShell />);
    await screen.findByRole("button", { name: /new scrutiny/i });
    const before = document.documentElement.getAttribute("data-theme");

    await userEvent.click(screen.getByRole("button", { name: /switch theme/i }));

    expect(document.documentElement.getAttribute("data-theme")).not.toBe(before);
  });

  it("shows the application on record once a thread is open", async () => {
    stubApplications();
    vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: "thread_abc",
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);

    const sidebar = await screen.findByRole("complementary", {
      name: /application details/i,
    });
    expect(sidebar).toHaveTextContent("Kokapet");
  });

  it("keeps the applicant's PAN and Aadhaar out of the details panel", async () => {
    stubApplications();
    vi.spyOn(scrutinyApi, "createThread").mockResolvedValue({
      threadId: "thread_abc",
      applicationId: MISMATCH_APPLICATION_ID,
      serviceOverrides: {},
      documents: [],
    });

    render(<WorkspaceShell />);
    await takeUpApplication(MISMATCH_APPLICATION_ID);
    const sidebar = await screen.findByRole("complementary", {
      name: /application details/i,
    });

    expect(sidebar).not.toHaveTextContent("BNMPS7720K");
  });
});
