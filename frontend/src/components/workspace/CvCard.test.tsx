/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CvCard } from "./CvCard";

describe("CvCard", () => {
  it("asks for confirmation before replace and delete", async () => {
    const user = userEvent.setup();
    const onReplace = vi.fn();
    const onDelete = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    render(
      <CvCard
        state="parsed"
        document={{
          id: "cv-1",
          filename: "cv.txt",
          pageCount: 1,
          parsedAt: "2026-09-18T12:00:00Z",
        }}
        errorMessage={null}
        onUpload={vi.fn()}
        onReplace={onReplace}
        onDelete={onDelete}
        onRetry={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(confirmSpy).toHaveBeenCalled();
    expect(onDelete).not.toHaveBeenCalled();

    confirmSpy.mockReturnValue(true);
    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(onDelete).toHaveBeenCalledTimes(1);

    confirmSpy.mockRestore();
  });
});
