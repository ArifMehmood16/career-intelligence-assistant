/**
 * Phase 12.5 — additive frontend types for analysis, drafts, ranking, supporting docs.
 * @vitest-environment node
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const typesSource = readFileSync(
  path.join(path.dirname(fileURLToPath(import.meta.url)), "index.ts"),
  "utf8",
);

const REQUIRED_EXPORTS = [
  "export type RoleStatus",
  "export interface AnalysisJob",
  "export interface GapPlan",
  "export interface GapItem",
  "export interface InterviewPack",
  "export interface DraftProvenance",
  "export interface BulletDraft",
  "export interface CoverLetterDraft",
  "export interface RankedRole",
  "export interface Comparison",
  "export interface SupportingDocument",
] as const;

describe("additive frontend types (12.5)", () => {
  it.each(REQUIRED_EXPORTS)("declares %s", (snippet) => {
    expect(typesSource).toContain(snippet);
  });

  it("adds Role.status and Role.updatedAt without removing existing fields", () => {
    const roleBlock = typesSource.match(
      /export interface Role\s*\{([\s\S]*?)\n\}/,
    )?.[1];
    expect(roleBlock).toBeDefined();
    expect(roleBlock).toMatch(/status:\s*RoleStatus/);
    expect(roleBlock).toMatch(/updatedAt:\s*string/);
    expect(roleBlock).toMatch(/fitScore:\s*number/);
    expect(roleBlock).toMatch(/bandLabel:\s*string/);
  });

  it("keeps ChatMessage persisted fields", () => {
    expect(typesSource).toMatch(
      /export interface ChatMessage\s*\{[^}]*conversationId\??:\s*string/s,
    );
    expect(typesSource).toMatch(
      /export interface ChatMessage\s*\{[^}]*createdAt\??:\s*string/s,
    );
    expect(typesSource).toMatch(
      /export interface ChatMessage\s*\{[^}]*leftMachine:\s*boolean/s,
    );
  });
});
