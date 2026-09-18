import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BrandMark } from "./BrandMark";

describe("BrandMark", () => {
  it("exposes the product name for assistive tech", () => {
    render(<BrandMark />);
    expect(
      screen.getByRole("img", { name: "Career Intelligence" }),
    ).toBeInTheDocument();
  });
});
