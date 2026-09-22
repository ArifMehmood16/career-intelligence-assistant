/**
 * @vitest-environment node
 */
import { describe, expect, it } from "vitest";

import {
  citationNumberBySpanId,
  numberLetterCitations,
} from "./letterCitations";

describe("numberLetterCitations", () => {
  it("assigns stable numbers by first appearance and dedupes", () => {
    const numbered = numberLetterCitations([
      { spanIds: ["span-a", "span-b"] },
      { spanIds: ["span-a", "span-c"] },
    ]);
    expect(numbered).toEqual([
      { number: 1, spanId: "span-a" },
      { number: 2, spanId: "span-b" },
      { number: 3, spanId: "span-c" },
    ]);
    expect(citationNumberBySpanId(numbered).get("span-a")).toBe(1);
  });
});
