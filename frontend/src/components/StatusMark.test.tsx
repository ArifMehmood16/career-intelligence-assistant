import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusMark } from "./StatusMark";

describe("StatusMark", () => {
  it("renders the status word alongside the glyph", () => {
    render(<StatusMark status="missing" />);
    expect(screen.getByText("Missing")).toBeInTheDocument();
  });

  it("keeps met status readable without relying on colour alone", () => {
    render(<StatusMark status="met" />);
    expect(screen.getByText("Met")).toBeInTheDocument();
  });
});
