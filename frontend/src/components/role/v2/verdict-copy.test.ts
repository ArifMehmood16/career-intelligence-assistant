/**
 * PLAN 18.13 — words for the judge's scores and the server's adjustments.
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest";

import {
  adjustmentLabel,
  anchorLabel,
  bandLabel,
  NOT_STATED,
} from "./verdict-copy";

describe("v2 verdict copy", () => {
  it("names each score by the anchor the judge was given", () => {
    expect(anchorLabel("match", 3)).toBe("The requirement as stated");
    expect(anchorLabel("seniority", 0)).toBe("Two or more levels below");
    expect(anchorLabel("experience", 4)).toBe("Clearly exceeds the years");
  });

  it("says why a dimension has no score", () => {
    expect(NOT_STATED.seniority).toBe("The advert states no level.");
    expect(NOT_STATED.experience).toBe("The advert states no years.");
  });

  it("explains each server rule that changed a verdict", () => {
    expect(adjustmentLabel("match_capped_skills_only")).toBe(
      "Match capped at 2: only a skills line supports it.",
    );
    expect(adjustmentLabel("verdict_lowered_to_partial")).toBe(
      "Verdict lowered to partial by the server's rules.",
    );
    expect(adjustmentLabel("something_new")).toBe("something_new");
  });

  it("labels the band", () => {
    expect(bandLabel("strong")).toBe("Strong match");
    expect(bandLabel("limited")).toBe("Limited match");
  });
});
