/**
 * PLAN 13D.6e — incomplete analysis is not a fit score.
 */

export const INCOMPLETE_ANALYSIS_CODES = new Set([
  "assessment_incomplete",
  "extraction_incomplete",
]);

export function isIncompleteAnalysisCode(code: string | null | undefined): boolean {
  return Boolean(code && INCOMPLETE_ANALYSIS_CODES.has(code));
}

export function incompleteAnalysisTitle(code: string | null | undefined): string {
  return isIncompleteAnalysisCode(code) ? "Analysis incomplete" : "Analysis failed";
}

export function incompleteAnalysisDetail(code: string | null | undefined): string {
  if (code === "assessment_incomplete") {
    return "The CV was not fully assessed. This is not a fit judgement.";
  }
  if (code === "extraction_incomplete") {
    return "The documents were not fully classified. This is not a fit judgement.";
  }
  return "Try running the analysis again.";
}
