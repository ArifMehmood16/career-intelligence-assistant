/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoverLettersCard } from "./CoverLettersCard";

const base = {
  documents: [] as [],
  errorMessage: null as string | null,
  uploading: false,
  onUpload: vi.fn(),
  onDelete: vi.fn(),
  onRetry: vi.fn(),
};

describe("CoverLettersCard", () => {
  it("states that cover letters are not score evidence", () => {
    render(<CoverLettersCard {...base} state="ready" />);

    expect(
      screen.getByText(/never used as evidence for fit scores/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/no supporting cover letters uploaded yet/i),
    ).toBeInTheDocument();
  });

  it("shows an actionable error state", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <CoverLettersCard
        {...base}
        state="error"
        errorMessage="Upload failed."
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText("Upload failed.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalled();
  });
});
