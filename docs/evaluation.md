# Evaluation

Retrieval, extraction and generation quality are claims. This file is where they are
evidenced. No number appears here that was not observed from a recorded run.

## Dataset

`sample-data/evaluation/dataset.json`. Synthetic CVs and job descriptions only — never
a real person's document. The stub cases reference ids from
`sample-data/fixtures/manifest.json`; labels are starting points until Phase 14
measures them.

Each case carries:

| Field | Meaning |
|---|---|
| `cv_id` | Fixture CV under test |
| `job_id` | Fixture job description under test |
| `expected_requirements` | Requirements a correct extraction must find |
| `expected_absent` | Text that must **not** be extracted as a requirement |
| `expected_mapping` | Requirement id to `met` / `partial` / `missing` |
| `expected_reasons` | Requirement id to the mapping reason code, where it is determinate |
| `questions` | Question, expected intent, and whether evidence exists |
| `generation_probes` | Facts that must not appear in a draft — the adversarial set |

## Metrics

| Metric | Definition | Threshold |
|---|---|---|
| `requirement_precision` | Extracted requirements that are real requirements | TBD |
| `requirement_recall` | Expected requirements that were found | TBD |
| `mapping_accuracy` | Mapping outcomes matching the label | TBD |
| `citation_validity_rate` | Citations resolving to a stored span | 1.0 — no exceptions |
| `insufficient_evidence_correct_rate` | Unanswerable questions correctly refused | TBD |
| `score_stability` | Identical inputs produce an identical score | 1.0 — no exceptions |
| `groundedness_violation_rate` | Drafts containing a fact absent from their cited spans | 0.0 at the response boundary |
| `template_fallback_rate` | Drafts served from the template path after two failed validations | TBD |

Three metrics are not negotiable. A citation that does not resolve is a fabrication, a
score that moves between identical runs is not a score, and a draft that reaches the
user containing an invented fact is the one failure this product exists to prevent.

`groundedness_violation_rate` is measured at the **response boundary** and must be
zero: the validator fails closed, so a violating draft is never served. The interesting
number is `template_fallback_rate`, which is how often a provider had to be caught —
that one is reported, not bounded.

## Runs

Record provider configuration, date and observed numbers. One row per run.

| Date | Embeddings | Extractor | req. precision | req. recall | mapping acc. | citation validity | insuff. correct |
|---|---|---|---|---|---|---|---|
| TBD | — | — | — | — | — | — | — |

## Provider comparison

The same dataset, the same code path, one provider at a time. This is the table that
answers "does this actually need a frontier model?" — and the honest answer is
sometimes no, which is exactly why it is worth publishing.

| Date | Completion | Embeddings | req. P / R | mapping acc. | citation validity | p50 latency | p95 latency | Cost / question |
|---|---|---|---|---|---|---|---|---|
| TBD | hermetic | lexical | — | — | — | — | — | 0.00 |
| TBD | ollama | ollama | — | — | — | — | — | 0.00 |
| TBD | openai | openai | — | — | — | — | — | — |
| TBD | anthropic | ollama | — | — | — | — | — | — |

## Generation comparison

Drafting is where a better model should show most, and where a worse one is most
dangerous. Measured separately because the failure mode is different: not a wrong
answer, a plausible one.

| Date | Completion | Bullets: fallback rate | Letter: fallback rate | Refusals correct | p50 latency | Cost / draft |
|---|---|---|---|---|---|---|
| TBD | hermetic (template) | n/a | n/a | — | — | 0.00 |
| TBD | ollama | — | — | — | — | 0.00 |
| TBD | openai | — | — | — | — | — |
| TBD | anthropic | — | — | — | — | — |

`Refusals correct` is the share of cover-letter requests below the two-met-must-have
threshold that were correctly refused. A provider cannot influence this — it is
decided in domain code — so a non-perfect number here is a bug, not a provider
difference, and that is exactly why the column is present.

## Rules for every table here

- One variable at a time. Changing the completion and embedding providers together
  produces a number that explains nothing.
- Cost is computed from recorded token counts, not estimated from a price page.
- Latency is measured on one machine. It compares configurations; it is not a
  production figure.
- A local configuration that matches a hosted one stays in the table and gets called
  out. That row is the most useful one for anyone deciding what to deploy.
- The deterministic score is provider-independent by design. A provider only moves
  these numbers through extraction quality, which is the point of measuring it here
  rather than at the score.

## Current-policy baseline (Phase 13D.1)

Measured on 2026-09-22 against `sample-data/evaluation/dataset.json` pilot
`evidence-assessment-v1`. The runner is `current_policy_baseline`: configured
rubric and similarity floor, empty embedding similarities, and `NullAdjudicator`.
No model was called. Labels were not changed. This is the hermetic path, not a
live Ollama accuracy figure.

| Quantity | Observed |
|---|---|
| Groups / roles / scoreable requirements | 17 / 20 / 24 |
| Assessment disagreements | 10 |
| Labelled non-`met` returned as `met` | 8 |
| Pairwise order disagreements | 1 |

The eight unsupported `met` results are keyword overlap without the labelled
scope, duration, negation, contradiction or aspiration: `dev-insufficient-scope`
(`req-python-leadership`), `dev-insufficient-duration`, `dev-negation`,
`dev-contradiction`, `dev-aspiration`, `heldout-sql-leadership`,
`heldout-insufficient-scope` and `heldout-negation`. `dev-overlap` is no longer
in that list: two concurrent Java posts are merged, so six labelled years stay
`partial`. Two paraphrases with no
shared keywords were labelled `met` and returned `missing`: `dev-paraphrase` and
`heldout-paraphrase`. The order miss is `heldout-ordering`: `heldout-spreadsheets`
scored 0 and `heldout-sql-leadership` scored 100, reversing the labelled order,
because that leadership requirement was one of the unsupported `met` results.

## Known measurement limits

- The fixture set is synthetic and small. It detects regressions; it does not prove
  general accuracy.
- Requirement labelling is a judgement call. The labels are one reviewer's reading.
- Each provider is measured separately and never averaged with another. An average
  across providers describes a system nobody is running.
- The groundedness validator has false positives — a legitimately rephrased figure, a
  company name in a new inflection. They surface as template fallbacks, which is the
  safe direction to be wrong in, and the rate is published rather than tuned away.
