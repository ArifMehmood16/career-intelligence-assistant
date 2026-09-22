/**
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest";

import {
  incompleteAnalysisDetail,
  incompleteAnalysisTitle,
  isIncompleteAnalysisCode,
} from "./analysis-status";

describe("incomplete analysis copy", () => {
  it("treats assessment and extraction incomplete codes as incomplete", () => {
    expect(isIncompleteAnalysisCode("assessment_incomplete")).toBe(true);
    expect(isIncompleteAnalysisCode("extraction_incomplete")).toBe(true);
    expect(isIncompleteAnalysisCode("provider_timed_out")).toBe(false);
  });

  it("labels incomplete analysis without calling it a fit score", () => {
    expect(incompleteAnalysisTitle("assessment_incomplete")).toBe(
      "Analysis incomplete",
    );
    expect(incompleteAnalysisDetail("assessment_incomplete")).toMatch(
      /not a fit judgement/i,
    );
    expect(incompleteAnalysisTitle("provider_timed_out")).toBe("Analysis failed");
  });
});
