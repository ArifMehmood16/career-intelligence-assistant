import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CiaMark } from "./CiaMark";

describe("CiaMark", () => {
  it("exposes the CIA label for assistive tech", () => {
    render(<CiaMark />);
    expect(screen.getByRole("img", { name: "CIA" })).toBeInTheDocument();
  });
});
