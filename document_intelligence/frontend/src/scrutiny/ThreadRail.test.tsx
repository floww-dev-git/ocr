import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { buildApplication } from "@/test/factories";
import { ThreadRail, type RailThreadState } from "./ThreadRail";

const APP_A = buildApplication({
  applicationId: "BN/2026/0421",
  fieldValues: { applicantName: "Srinivas Rao Kandula", village: "Bachupally" },
});
const APP_B = buildApplication({
  applicationId: "BN/2026/0377",
  fieldValues: { applicantName: "Mohammed Irfan Siddiqui", village: "Kokapet" },
});

function renderRail(
  overrides: {
    threadState?: Record<string, RailThreadState>;
    selectedApplicationId?: string | null;
    onSelectApplication?: (id: string) => void;
    onRename?: (id: string, title: string) => void;
    onDelete?: (id: string) => void;
    onNewScrutiny?: () => void;
    applications?: typeof APP_A[];
  } = {},
) {
  return render(
    <ThreadRail
      applications={overrides.applications ?? [APP_A, APP_B]}
      selectedApplicationId={overrides.selectedApplicationId ?? null}
      onSelectApplication={overrides.onSelectApplication ?? (() => {})}
      onCollapse={() => {}}
      loading={false}
      threadState={overrides.threadState ?? {}}
      onRename={overrides.onRename ?? (() => {})}
      onDelete={overrides.onDelete ?? (() => {})}
      onNewScrutiny={overrides.onNewScrutiny ?? (() => {})}
    />,
  );
}

describe("the thread rail", () => {
  it("opens the application the officer picks", async () => {
    const onSelectApplication = vi.fn();
    renderRail({ onSelectApplication });

    await userEvent.click(
      screen.getByRole("button", { name: /Srinivas Rao Kandula/i }),
    );

    expect(onSelectApplication).toHaveBeenCalledWith("BN/2026/0421");
  });

  it("shows a count pill only for an application with open items", () => {
    renderRail({
      threadState: {
        "BN/2026/0377": {
          status: "attention",
          openCount: 2,
          openedAt: Date.now(),
          title: null,
        },
      },
    });

    const attention = screen.getByRole("button", {
      name: /Mohammed Irfan Siddiqui/i,
    });
    expect(within(attention).getByText("2")).toBeInTheDocument();
    // The other row has nothing open, so no pill.
    const clean = screen.getByRole("button", { name: /Srinivas Rao Kandula/i });
    expect(within(clean).queryByText("2")).not.toBeInTheDocument();
  });

  it("shows when an application was last opened", () => {
    renderRail({
      threadState: {
        "BN/2026/0421": {
          status: "clear",
          openCount: 0,
          openedAt: Date.now() - 5 * 60_000,
          title: null,
        },
      },
    });

    expect(
      within(screen.getByRole("button", { name: /Srinivas Rao Kandula/i })).getByText(
        /5 min ago/i,
      ),
    ).toBeInTheDocument();
  });

  it("shows an officer's rename in place of the id", () => {
    renderRail({
      threadState: {
        "BN/2026/0421": {
          status: "clear",
          openCount: 0,
          openedAt: null,
          title: "Kandula — apartment",
        },
      },
    });

    expect(screen.getByText("Kandula — apartment")).toBeInTheDocument();
  });

  it("removes an application from the list when the officer deletes it", async () => {
    const onDelete = vi.fn();
    renderRail({ onDelete });

    // Open the row's menu, then delete.
    const row = screen.getByRole("button", { name: /Srinivas Rao Kandula/i });
    await userEvent.click(within(row).getByRole("button", { name: /thread options/i }));
    await userEvent.click(screen.getByRole("menuitem", { name: /delete/i }));

    expect(onDelete).toHaveBeenCalledWith("BN/2026/0421");
  });

  it("asks for the picker when New scrutiny is pressed", async () => {
    const onNewScrutiny = vi.fn();
    renderRail({ onNewScrutiny });

    await userEvent.click(screen.getByRole("button", { name: /new scrutiny/i }));

    expect(onNewScrutiny).toHaveBeenCalledTimes(1);
  });

  it("says how to begin when nothing has been taken up", () => {
    renderRail({ applications: [] });

    expect(screen.getByText(/press new scrutiny to take up/i)).toBeInTheDocument();
  });

  it("filters the list by what the officer types", async () => {
    renderRail();

    await userEvent.type(
      screen.getByRole("searchbox", { name: /search applications/i }),
      "Kokapet",
    );

    expect(
      screen.getByRole("button", { name: /Mohammed Irfan Siddiqui/i }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Srinivas Rao Kandula/i }),
    ).not.toBeInTheDocument();
  });
});
