# ADR 004 — The fit score is computed, not generated

- Status: accepted
- Date: 2026-09-18

## Context

Asking a language model for a fit score produces a number that changes between runs,
cannot be explained component by component, and tends to flatter. A candidate acting
on it has no way to check it.

## Decision

The model extracts requirements and claims. Domain code decides whether each
requirement is met, partial or missing, and computes the score arithmetically from
that mapping using a documented rubric.

No model output becomes a score. No claim about the candidate reaches the user
without a stored span that supports it.

## Consequences

- The score is reproducible and every component is traceable to specific text.
- The rubric's weights are a visible, arguable decision rather than a hidden one.
- Extraction errors surface as wrong mappings, which the evaluation harness measures,
  instead of hiding inside a plausible paragraph.
- The product cannot tell the user what they want to hear.
