# ADR 014 — The model judges three dimensions; the domain aggregates the score

- Status: accepted (PLAN 18.0, 2026-09-29)
- Date: 2026-09-29
- Plan: 18.7–18.9
- Design: [architecture-v2.md §8–§9](../architecture-v2.md#8-the-matching-workflow-and-the-model-judge)

## Context

[ADR 004](004-deterministic-scoring.md) keeps the fit score out of the model's hands,
and [ADR 011](011-evidence-assessment-contract.md) lets the model assess retrieved
evidence as `met`, `partial` or `missing`. That three-point assessment was already a
model judgement; it simply had no room for the two things a hiring manager weighs
beside relevance — whether the evidence is at the right level, and whether there is
enough of it. v1 pushed those into rules: work-verb gates, a skills-line special
case, "Lead" as an opening word only.

Those rules are brittle, and they still cannot tell a senior engineer who led a
migration from a junior one who took part in it. That is a language judgement.

The properties ADR 004 protects are still the right ones: a number the candidate
can check, reproduced on replay, with every component traceable to text.

## Decision

1. **The model judges each atomic requirement on three anchored integer scales,
   0–4:** match, seniority and experience. Seniority and experience are `null`
   exactly when the requirement's verified `seniority_expected` or `years_expected`
   is null. The judge also returns
   a verdict (`met`, `partial`, `missing`), unmet conditions, a contradiction flag
   and retrieval feedback.
2. **Every non-zero match score quotes the evidence.** Each quote must appear
   verbatim in a chunk that retrieval gave the judge for that requirement.
   Seniority and experience are judged against supplied facts.
3. **The server validates before anything is stored:** complete and unique verdicts,
   cited ids within the candidate set, verbatim quotes, verdict and match score
   consistent (`missing` ⇔ match ≤ 1, `met` ⇒ match ≥ 3), and `null` dimensions
   exactly when the requirement states no level or years. When only `skills` chunks
   are cited, match is capped at 2 and experience at 1, except that a requirement
   stating no years or level whose technology terms all appear on that line may
   reach match 3 — v1's decided rule for a bare tool name (log entry 136). A
   contradiction caps match at 2 and the verdict at `partial`. Every cap is
   recorded. One repair call; a second failure makes the analysis incomplete.
4. **Facts are computed, not judged.** Years of experience per technology come from
   the knowledge graph's date-interval union in domain code, labelled as upper
   bounds, with "present" resolved to the analysis's `as_of` date, and are given to
   the judge. The judge decides whether those years and that depth meet the requirement;
   it never supplies a duration.
5. **The domain aggregates.** A requirement's score is the weighted mean of its
   applicable dimensions, where 3 ("as stated") is full credit and 4 earns no
   bonus, times the v1 recency factor, and zero when the verdict is `missing`. The fit score is the must-have-weighted mean of requirement scores.
   A must-have with match ≤ 1 caps the band at partial. Weights live in
   `config/scoring_rubric.toml` version `scoring-rubric-v2`.
6. **Replay is exact.** Verdicts are cached under a hash of prompt and anchor
   versions, provider, model tag and the model digest where the provider exposes
   one, the requirement and its facts including the `as_of` date, and the ordered
   candidate chunks; search orderings break ties on chunk id. Re-analysing unchanged
   inputs reuses the stored verdict, so `score_stability` on replay is 1.0 by
   construction. Fresh-run variability is measured as `judge_stability` and
   reported. The rubric is not in the key: aggregation is recomputed from cached
   verdicts.
7. **Keyword coverage is shown, not scored.** Exact, alias-only and missing
   technology terms are reported next to the fit score. The judge already sees them,
   so adding them to the score would count them twice.

This amends ADR 004's "no model output becomes a score": the model's per-dimension
judgements are inputs, and the fit score, bands, ranking and gap order remain
arithmetic in domain code. It supersedes the assessor contract in ADR 011 decision 1
and the skills-line amendment to ADR 011, once Phase 18.15 retires the v1 path.
ADR 011's letter policy and its rule that a generated draft never raises the score
are unchanged.

## Consequences

- Seniority and tenure are judged where they can be judged, with a rationale and a
  quote, instead of approximated by word lists.
- Each requirement's score decomposes into three numbers a candidate can dispute,
  each tied to a quote. The weights that combine them are visible configuration.
- A judge can be wrong in a new way: a plausible rationale over a real quote that
  does not support it. The evaluation measures that directly — agreement with human
  labels per dimension and the unsupported `met` rate — rather than trusting the
  validator.
- Fresh runs of the same model may disagree. Replay does not; the cache makes the
  published score reproducible, and the variability is a published number.
- The judge prompt is a versioned contract. Changing it or the anchors invalidates
  the verdict cache by construction; changing the rubric re-scores from cached
  verdicts without re-judging.
- Requirements per judge call come from the provider's capability descriptor, so a
  hosted model can judge a role in one call and a local model in several.

## Rejected alternatives

- **Let the model return the fit score.** Unreproducible, not decomposable, and it
  flatters. ADR 004's reasoning stands for the aggregate.
- **Dividing by the top of the scale.** With 4 as full credit, a candidate who
  meets every requirement exactly would score 75, on the band boundary. 3 is "meets
  as stated", so 3 is full credit.
- **A 0–100 score per dimension.** False precision; anchored small integer scales
  are easier for a model to apply consistently and for a reviewer to check.
- **Keep seniority and experience as domain rules.** That is the v1 approach, and
  the amendment history is the evidence against it.
- **Let the judge compute years from the text.** Date arithmetic is not a language
  task; the domain already parses dates and can take the union of overlapping roles.
- **Fold keyword coverage into the score.** Double counting, and it would reward
  keyword stuffing.
