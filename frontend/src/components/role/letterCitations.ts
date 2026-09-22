/** Stable [1]-style citation numbers for cover-letter span ids. */

export interface NumberedSpan {
  number: number;
  spanId: string;
}

export function numberLetterCitations(
  paragraphs: ReadonlyArray<{ spanIds: ReadonlyArray<string> }>,
): NumberedSpan[] {
  const seen = new Map<string, number>();
  const ordered: NumberedSpan[] = [];
  for (const paragraph of paragraphs) {
    for (const spanId of paragraph.spanIds) {
      if (!spanId || seen.has(spanId)) continue;
      const number = seen.size + 1;
      seen.set(spanId, number);
      ordered.push({ number, spanId });
    }
  }
  return ordered;
}

export function citationNumberBySpanId(
  numbered: ReadonlyArray<NumberedSpan>,
): Map<string, number> {
  return new Map(numbered.map((item) => [item.spanId, item.number]));
}
