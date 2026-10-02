# Feature Specification: Display published recency gaps

**Feature Branch**: `fix/phase-19-recency-gap-display`
**Created**: 2026-10-02
**Status**: Implemented for review; tests/lint deferred
**Input**: Completed analysis shows score/counts, but detailed Fit and Gaps fail to load.
**Root scope**: [PLAN 19.1](../../PLAN.md#191--retire-the-competing-analysis); verification under 19.4.

## User Scenarios & Testing

### User Story 1 — Read complete Fit and Gaps (Priority: P1)

A candidate can read all published judgments and gap suggestions when the domain
identifies older/undated evidence as the biggest opportunity for improvement.

**Why this priority**: One valid gap category currently blocks the whole detail view.
**Independent Test**: Feed a synthetic published result containing a recency gap
through the HTTP client and both detail panes. Execute only when checks resume.

**Acceptance Scenarios**:

1. Given a finished publication with a recency gap, when the browser reads it,
   then Fit and Gaps accept it and show the existing judgments/score.
2. Given a recency gap with current factor 0.6, when displayed, then it is labelled
   evidence recency and shows 60% current weight, not a judge anchor out of four.
3. Given another gap dimension, when displayed, then the existing anchor scale stays.
4. Given an unknown dimension, when read, then response validation still rejects it.

### Edge Cases

- Mixed match/seniority/experience/recency gaps; zero/fractional recency factors.
- No gaps, incomplete analysis and API errors retain their existing states.
- A cached failed response after hot reload may need Retry or a page refresh.

## Requirements

- **FR-001**: The client MUST accept exactly the domain's four gap dimensions.
- **FR-002**: Recency MUST be a gap category separate from the three judge dimensions.
- **FR-003**: Recency's current value MUST show its 0–1 weighting factor as a percent;
  judge gaps MUST retain their 0–4 anchor scale. Server delta order stays unchanged.
- **FR-004**: No score recomputation, model call, stored publication or evidence
  validation changes are permitted. Existing data MUST render without reanalysis.
- **FR-005**: Regression cases MUST be authored; tests/lint remain deferred.

### Key Entities

- Published gap: requirement identifier, dimension, current value and score delta.
- Gap dimension: match/seniority/experience/recency; judge dimensions exclude recency.

## Success Criteria

- **SC-001**: The current published response passes client validation after repair.
- **SC-002**: Both detail panes can read a recency-containing result; recency is
  labelled and displayed on the proper scale.
- **SC-003**: Unknown dimensions remain invalid, and no reanalysis is required.

## Assumptions

Use the current consolidated baseline 5e67682, which contains required repairs;
main lacks that work. Read-only local HTTP/schema diagnosis is allowed by the debug
request; it does not replace deferred suites or release gates. No personal payload
is printed/saved or sent to a model provider.
