/**
 * Words for a verdict: the judge's 0–4 anchors, and the rules the server applied.
 * The anchors are the ones in the judge prompt (`judge-anchors-v1`), so a score
 * reads here the way the model was told to give it.
 */
import type { JudgeDimension } from "@/types";

export const MAX_SCORE = 4;

export const DIMENSION_LABEL: Record<JudgeDimension, string> = {
  match: "Match",
  seniority: "Seniority",
  experience: "Experience",
};

const ANCHORS: Record<JudgeDimension, readonly string[]> = {
  match: [
    "Nothing relevant",
    "Adjacent area only",
    "Part of the requirement shown",
    "The requirement as stated",
    "Beyond it in scope or outcome",
  ],
  seniority: [
    "Two or more levels below",
    "One level below",
    "One level below, with ownership shown",
    "At the level",
    "Above the level",
  ],
  experience: [
    "None",
    "Listed only, or under half the years",
    "At least half the years",
    "Meets the years",
    "Clearly exceeds the years",
  ],
};

export const NOT_STATED: Record<"seniority" | "experience", string> = {
  seniority: "The advert states no level.",
  experience: "The advert states no years.",
};

const ADJUSTMENTS: Record<string, string> = {
  match_capped_skills_only:
    "Match capped at 2: only a skills line supports it.",
  experience_capped_skills_only:
    "Experience capped at 1: only a skills line supports it.",
  match_capped_contradiction: "Match capped at 2: the CV contradicts it.",
  verdict_lowered_to_partial:
    "Verdict lowered to partial by the server's rules.",
};

const BANDS: Record<string, string> = {
  strong: "Strong match",
  partial: "Partial match",
  limited: "Limited match",
};

export function anchorLabel(dimension: JudgeDimension, score: number): string {
  return ANCHORS[dimension][score] ?? `${score} of ${MAX_SCORE}`;
}

export function adjustmentLabel(code: string): string {
  return ADJUSTMENTS[code] ?? code;
}

export function bandLabel(band: string): string {
  return BANDS[band] ?? band;
}
