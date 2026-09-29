/** A v2 fit and one retrieval trace, as the verdict routes send them (PLAN 18.13). */
import type { RetrievalTrace, RoleVerdicts } from "@/types";

export const VERDICTS: RoleVerdicts = {
  roleId: "role-1",
  analysisId: "an-1",
  fitScore: 71.4,
  band: "partial",
  gated: true,
  rubricVersion: "scoring-rubric-v2",
  leftMachine: false,
  verdicts: [
    {
      requirementId: "r1",
      quote: "5+ years of Python",
      statement: "Has five or more years of Python.",
      mustHave: true,
      verdict: "partial",
      requirementScore: 0.5,
      match: { score: 3, rationale: "Python in two roles." },
      seniority: null,
      experience: { score: 2, rationale: "About three years shown." },
      unmetConditions: ["five years"],
      contradiction: false,
      adjustments: [],
      evidence: [
        { chunkId: "c1", documentId: "cv-1", quote: "Wrote Python utilities" },
      ],
      provider: "ollama",
      model: "qwen2.5:7b",
    },
  ],
  keywordCoverage: {
    exact: ["Python"],
    alias: ["Postgres"],
    missing: ["Kafka"],
  },
  gapPlan: [
    { requirementId: "r1", dimension: "experience", current: 2, delta: 6.5 },
  ],
};

export const TRACE: RetrievalTrace = {
  requirementId: "r1",
  rounds: [
    {
      round: 0,
      queryText: "Has five or more years of Python.",
      hits: [
        {
          chunkId: "c1",
          fusedScore: 0.0328,
          denseRank: 1,
          lexicalRank: 2,
          exactRank: 1,
        },
        {
          chunkId: "c2",
          fusedScore: 0.0161,
          denseRank: 3,
          lexicalRank: null,
          exactRank: null,
        },
      ],
    },
    {
      round: 1,
      queryText: "Python data tooling in production",
      hits: [
        {
          chunkId: "c3",
          fusedScore: 0.0164,
          denseRank: 1,
          lexicalRank: null,
          exactRank: null,
        },
      ],
    },
  ],
};
