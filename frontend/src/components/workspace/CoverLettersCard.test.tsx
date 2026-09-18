/**
 * @vitest-environment jsdom
 */
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CoverLettersCard } from "./CoverLettersCard";

describe("CoverLettersCard", () => {
  it("states that cover letters are not score evidence", () => {
    render(
      <CoverLettersCard
        state="ready"
        documents={[]}
        errorMessage={null}
        uploading={false}
        onUpload={vi.fn()}
        onDelete={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(
      screen.getByText(/never used as evidence for fit scores/i),
    ).toBeInTheDocument();
  });
});
