# Research decisions
Inspected current code and tests; Spec Kit research agent confirmed preservation
paths and numeric-null restriction. No external API/library change to research.

- Stored score explanation already contains original weights/contributions;
  project those through domain normalization instead of recalculating a rubric.
- Existing experience rule requires years and omits qualitative depth. Add verified
  optional expectation and qualitative anchors; never manufacture numerical years.
- Whole CV work/JD context belongs in the same judge prefix and cache/budget. Facts
  survive repairs/correction already. Exclude contact and keep citation eligibility.
- Existing SQL JSON fields can carry expectation/context-display fields with .get
  defaults. No schema migration or extra provider call is needed.
- Ask already sets sending before dispatch but shows no pending status. Reuse state
  and explicitly cover response silence, stream, refetch, stop and errors.
Rejected: browser score recomputation, copying all tenure across tools, fabricated
progress, a second scoring pipeline and hosted personal-document development calls.
