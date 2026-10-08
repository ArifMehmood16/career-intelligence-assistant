import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AddRoleDialog } from "./AddRoleDialog";

afterEach(cleanup);

async function setup() {
  const user = userEvent.setup();
  const onSubmit = vi.fn();
  render(
    <AddRoleDialog
      open
      disabled={false}
      submitting={false}
      onOpenChange={vi.fn()}
      onSubmit={onSubmit}
    />,
  );
  await user.type(screen.getByLabelText("Role title"), "Data Engineer");
  await user.type(screen.getByLabelText("Company"), "Northwind");
  const add = () =>
    within(screen.getByRole("dialog")).getByRole("button", {
      name: "Add role",
    });
  return { user, onSubmit, add };
}

describe("AddRoleDialog", () => {
  it("rejects empty files and permits a usable replacement", async () => {
    const { user, onSubmit, add } = await setup();
    const input = screen.getByLabelText("Job description file");
    await user.upload(
      input,
      new File(["  "], "empty.txt", { type: "text/plain" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "must contain plain",
    );
    expect(add()).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
    await user.upload(
      input,
      new File(["Build APIs."], "valid.txt", { type: "text/plain" }),
    );
    await waitFor(() => expect(add()).toBeEnabled());
    await user.click(add());
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ description: "Build APIs." }),
    );
  });

  it("submits the selected text file contents rather than its filename", async () => {
    const { user, onSubmit, add } = await setup();
    await user.upload(
      screen.getByLabelText("Job description file"),
      new File(["Build Python APIs and test data pipelines."], "role.txt", {
        type: "text/plain",
      }),
    );
    await waitFor(() => expect(add()).toBeEnabled());
    await user.click(add());
    expect(onSubmit).toHaveBeenCalledWith({
      title: "Data Engineer",
      company: "Northwind",
      description: "Build Python APIs and test data pipelines.",
    });
  });

  it("keeps pasted input available when submission has not succeeded", async () => {
    const { user, onSubmit, add } = await setup();
    await user.click(screen.getByRole("tab", { name: "Paste text" }));
    await user.type(
      screen.getByLabelText("Job description"),
      "Build Python APIs.",
    );
    await user.click(add());
    expect(onSubmit).toHaveBeenCalledOnce();
    expect(screen.getByLabelText("Role title")).toHaveValue("Data Engineer");
    expect(screen.getByLabelText("Job description")).toHaveValue(
      "Build Python APIs.",
    );
  });
});
