import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

/**
 * Takes an application up onto the rail the way an officer does: press New
 * scrutiny, choose it out of the queue, then start.
 *
 * The rail begins empty — the queue is not the officer's workload until they pick
 * from it — so every test that needs an open thread goes through here.
 */
export async function takeUpApplication(applicationId: string): Promise<void> {
  await userEvent.click(
    await screen.findByRole("button", { name: /new scrutiny/i }),
  );
  const queue = await screen.findByRole("list", {
    name: /applications in the queue/i,
  });
  await userEvent.click(await within(queue).findByText(applicationId));
  await userEvent.click(screen.getByRole("button", { name: /start scrutiny/i }));
}
