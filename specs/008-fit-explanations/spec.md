# Feature Specification: Fit explanations and responsive Ask

**Feature Branch**: `feat/phase-19-fit-explanations`
**Created**: 2026-10-06
**Status**: Implemented and verified; PR #46, CI green on d579923
**Input**: Show green/red score contribution arrows, judge experience/seniority
in overall CV/JD context, and show processing immediately in Ask.
Root scope: bounded human-assigned group under PLAN 19.1–19.3 and BACKLOG Now.

## User Scenarios & Testing

### US1 — Understand point impact (P1)
Candidates see how each met, partial or missing requirement affects overall fit.
Independent test: weighted requirements show earned and unearned points; totals
reconcile to published fit and full credit. Filtering does not change attribution.
Acceptance: a partial requirement displays both labelled arrows; missing earns
zero; full credit loses zero; unavailable attribution is not fabricated as zero.

### US2 — Assess requested experience in context (P1)
Candidates see what level/depth the advert asks and what their career evidence
supports, including qualitative experience requirements without stated years.
Independent test: qualitative production experience is assessed without inventing
tenure; role-wide context informs seniority while a tool-specific years threshold
does not spread to other requirements. Unsupported expectations are discarded.

### US3 — See Ask processing immediately (P1)
Candidates see a processing indicator after sending, before the backend responds.
Independent test: hold the response before its first event, then stream, complete,
fail or stop; visible status tracks the request and clears on terminal outcomes.

### Edge Cases
Older publications, valid zero, unknown attribution, recency discounts, weighted
must-haves, qualitative versus numeric experience, contact information, injected
document instructions, oversized context, cache reuse, failures and cancellation.

## Requirements

- FR-001: Show earned points with a green up arrow and unearned points with a red
  down arrow, with text/signs so color is not the sole meaning.
- FR-002: Attribution uses the published weighting and score; label its full-credit
  reference, preserve filters/order/evidence, and distinguish unknown from zero.
- FR-003: Judge experience and seniority using the overall JD and CV career
  context; keep evidence quotes grounded and document instructions untrusted.
- FR-004: Support verbatim qualitative experience expectations; numeric years
  remain explicit and requirement-specific. Explain asked versus supported scope.
- FR-005: Changes in visible career/JD context invalidate cached judgments;
  context must fit the bounded request budget, never silently truncate evidence.
- FR-006: Ask shows processing immediately before any response event, transitions
  during answering, and clears on success, failure or stop without duplicate sends.
- FR-007: Existing scoring/publication/privacy rules remain; previously published
  results remain readable and judgment changes require reanalysis.
- FR-008: Add meaningful regressions, current synthetic gallery states, current
  product/API docs and green commits on one clean branch.

### Key Entities
Published point share; verified requirement expectation; career/JD context;
pending Ask request and its terminal outcome.

## Success Criteria

- SC-001: Weighted earned shares sum to published fit; earned plus unearned shares
  sum to 100 within numeric precision, with no filtered-total recalculation.
- SC-002: Synthetic qualitative, numeric, contextual, unsupported and injection
  examples satisfy the same verified evidence rules without invented tenure.
- SC-003: A delayed Ask request displays processing before the first response and
  returns to an idle state on every tested terminal path.

## Assumptions
Red indicates shortfall from full credit, not a historical score decrease.
No new provider call/service/dependency or personal-document development request.
Qualitative experience uses delivery/depth anchors rather than years anchors.
Tests/lint are resumed; broader measured release gates remain separate.
