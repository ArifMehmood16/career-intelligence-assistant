# Evaluation

> Current status (2026-10-07): the measurements below are historical results for the
> retired analysis. The current one-call document reader, capacity-sized judge and
> parallel executor have not received a live quality/latency evaluation. Provider
> and runtime acceptance plus full lint/hermetic checks now pass (spec 010); those
> checks are not measurements of live model quality. PLAN 19.4
> records the remaining measurement gate; retirement is an approved product decision,
> not evidence that measured quality improved.

Retrieval, extraction and generation quality are claims. This file is where they are
evidenced. No number appears here that was not observed from a recorded run.

## Current analysis benchmark (PLAN 19.4)

Implemented 2026-10-02 in `career_assistant.ops.benchmark`, with its bounded
[feature spec](../specs/001-synthetic-analysis-benchmark/spec.md). **Offline execution observed 2026-10-07:**
[Saved report](evaluation-results/offline-2026-10-07.json) records 36 successful
observations: six shipped pairs, three cold/warm repetitions, no failures and zero
physical completion, embedding or metadata requests. Source was clean revision
`9c2f27e208b85184ae6308fc70f9397ff752c908`; inputs, rubric/model fingerprints,
frozen analysis date and prompt versions are in the report. Fixture providers were
`rules-v1` and `lexical-hash-v1`; fallback was disabled.

Command actually run:

```bash
make benchmark BENCHMARK_ARGS='--repetitions 3 --output /private/tmp/career-analysis-offline-20261007.json'
```

Per-pair cold p50 ranged from 1.575 to 1.970 ms; warm p50 from 0.622 to 0.872 ms.
The clean-match warm run reused two documents, nine vectors and all six verdicts,
with zero structured operations and one search embedding operation. These are
fixture observations, not production latency or model-quality measurements. This
closes only offline execution; frozen-label local-model quality remains open.

To reproduce another offline measurement, from the repository root:

```bash
make benchmark BENCHMARK_ARGS='--case clean_match --repetitions 3'
mkdir -p tmp
make benchmark BENCHMARK_ARGS='--case clean_match --output tmp/benchmark.json'
```

With no arguments the command selects every pairing in the shipped synthetic
`sample-data/fixtures/manifest.json`, runs each once cold and immediately warm, and
prints `analysis-benchmark-v1` JSON. `--case` is repeatable; `--repetitions` is bounded
to 1–20; `--as-of` defaults to the frozen date 2026-09-01. There is no arbitrary
CV/JD input option, and an existing output file is never overwritten.

Cold starts fresh document/vector/verdict caches and provider adapters. Warm retains
those identities, caches and analysis date. This does not unload an Ollama model,
reset a vendor prompt cache or simulate a fresh operating-system process. Measured
time includes harness/provider assembly, document reading, indexing, retrieval,
judging and domain scoring. Input loading, Git provenance, report serialization and
summary construction are outside that interval.

The harness executes the same `RoleAnalysisV2`, indexer, chunker, matcher, judge and
rubric as the application, with explicit fixture index/search/cache adapters.
**Fixture retrieval is used even in live-provider mode.** These observations measure
model plus application work; they exclude PostgreSQL, parsing binary uploads, queue
waiting and browser latency, and cannot establish production retrieval quality.

Every observation separates:

- `physical_attempts`: completion/embedding HTTP requests attempted at the existing
  transport boundary, including failed attempts and retries. GET model-metadata
  requests have their own bucket. Local Ollama HTTP is still a physical API attempt.
- `logical_operations`: structured and embedding method invocations; a structured
  invocation may contain schema repairs and several physical requests. Offline
  fixture operations produce zero physical attempts.
- `progress_attempts`: existing accounting scoped to analysis tasks. The offline
  structured fixture is instrumented as a fixture operation. These counts do not
  replace physical transport measurement; metadata lookups are outside progress.
- `cache_reuse`: document hits, existing vectors, verdict lookups and verdict hits.
  These are observed boundary events, not guessed savings. Warm search still embeds
  queries, and corrective retrieval may still do work.

Input/manifest/model-config/rubric fingerprints, source revision/dirty state,
Python/platform, actual provider/model tags and off-machine flags, selected settings,
capabilities, execution profiles and prompt/contract/rubric versions accompany the
measurements. Operational reports contain no evidence, prompts, responses, keys,
provider endpoints or raw exception text. Failure retains duration/counts, exposes
no fit score/band, skips its warm run and returns nonzero. Summaries use nearest-rank
p50/p95 per case and cold/warm group, exclude failed runs and state their counts.

Separately requested synthetic live work uses explicit provider selections:

```bash
make benchmark BENCHMARK_ARGS='--live --provider ollama --embedding-provider ollama --case clean_match'
```

Completion supports the existing Ollama/OpenAI/Anthropic builders; embeddings use
Ollama/OpenAI. Optional `--completion-model` and `--embedding-model` choose tags.
Only live mode loads existing provider settings; hosted requests still require
`ALLOW_HOSTED_PROVIDERS` and the selected provider's key. Automatic fallback is
disabled so a failed hosted run cannot become a fixture measurement. The command
does not enable hosted egress, migrate a database or read uploaded personal data.

### Frozen current-judge development labels

The historical dataset below does not define current truth. Spec 011 adds
`sample-data/evaluation/current-judge-labels.json`, version
`current-judge-development-v1`, frozen before any local-model execution. Eleven
full requirement clauses cover the adjacent-skills CV against the partial-match
and poor-match jobs; the ranking expectation compares these two jobs for that
same CV. These agent-authored development expectations require human calibration
before use as a release-quality threshold. No prompts were tuned against the labels.

`--quality` selects these two cases by default and emits `analysis-benchmark-v2`;
ordinary benchmark reports retain v1. Input SHA-256 values must match frozen labels
before model work. The report fingerprints both canonical label values and the
original label file. Quality calculation occurs after the timed analysis interval.

Quote matching normalizes whitespace, bullet prefix, case and final full stop;
it preserves punctuation such as C++. It does not infer equivalent clauses or
silently discard changed segmentation. Per observation, report expected/matched,
unmatched/unlabelled/duplicate requirements, absent verdicts and correct labels.
Agreement divides unique correct judgments by **all expected requirements**;
unmatched or duplicate clauses cannot improve it. Unsupported `met` counts fully
supported predictions against a labelled `partial` or `missing` expectation.
Its rate divides by labelled `met` predictions, and is null when none exist.
Unlabelled predictions remain visible and are excluded from that denominator.

Ranking agreement compares strict score ordering for the same CV, grouped by
repetition and cold/warm state. Both jobs must have successful published scores;
failed/skipped/missing results yield no eligible comparison. Ties do not satisfy
an expected strict ordering. Failure remains failure even if partial diagnostic
quality counts are available. These narrow metrics do not measure citation
semantic support, broad extraction accuracy or production retrieval quality.

```bash
make benchmark BENCHMARK_ARGS='--quality'
# Explicit synthetic local model work; keep hosted egress disabled.
make benchmark BENCHMARK_ARGS='--quality --live --provider ollama --embedding-provider ollama --completion-model qwen2.5:7b --embedding-model nomic-embed-text:latest'
```

Local execution results will be recorded here only after observation. The browser,
populated progress migration and private startup now have separate acceptance
evidence in the engineering journal; none establish live model quality.

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

These definitions are not results. Requirement precision, requirement recall and
mapping accuracy have not been measured. The table is the contract for a future
run. A dash or `TBD` means no observed number exists.

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
| Assessment disagreements | 7 |
| Labelled non-`met` returned as `met` | 5 |
| Pairwise order disagreements | 0 |

The five unsupported `met` results are keyword overlap without the labelled
duration, negation, contradiction or aspiration: `dev-insufficient-duration`,
`dev-negation`, `dev-contradiction`, `dev-aspiration` and `heldout-negation`.
An introductory course no longer meets a years-of-leadership requirement, so
`dev-insufficient-scope`, `heldout-insufficient-scope` and
`heldout-sql-leadership` left that list. `dev-overlap` stays `partial` because
concurrent jobs are one stretch of time. Two paraphrases with no shared
keywords were labelled `met` and returned `missing`: `dev-paraphrase` and
`heldout-paraphrase`. The labelled `heldout-ordering` pair no longer reverses,
because the leadership role is not scored as a match.

## Local Ollama measurement (Phase 13D.6, not a gate)

Measured on 2026-09-22 with `RUN_LLM_SMOKE=1` against the same pilot. Completion
was `llama3.2` and embeddings were `nomic-embed-text`, both on
`http://127.0.0.1:11434`. No API key was supplied. Every recorded call had
`left_machine` false. The runner is `measured_policy_baseline` with
`ModelAdjudicator`. Labels were not changed. Latency is per role, nearest-rank,
from that run.

| Quantity | Observed |
|---|---|
| Roles | 20 |
| Completion calls | 14 |
| Embedding calls | 19 |
| Assessment disagreements | 9 |
| Labelled non-`met` returned as `met` | 1 |
| Pairwise order disagreements | 1 |
| Per-role latency p50 / p95 | 1.72s / 3.93s |

The hermetic baseline on the same labels was 7 disagreements, 5 unsupported
`met` results and 0 order disagreements. This run reduced unsupported `met`
results to one and increased disagreements and order errors, so it does not
replace that baseline. The unsupported `met` is `role-partial` /
`req-reliability` (expected `partial`, observed `met`). The order error is
`dev-ordering`: `role-strong` scored 25 and `role-partial` scored 100.

The other disagreements were `role-strong` `req-dbt` (`met`/`partial`),
`role-strong` `req-sql` (`met`/`missing`), `dev-negation` `req-terraform`
(`missing`/`partial`), `dev-duplicate` `req-sql-a` and `req-sql-b`
(`met`/`missing`), `dev-paraphrase` `req-dba` (`met`/`missing`),
`dev-injection` `req-dbt-inj` (`met`/`missing`) and `heldout-paraphrase`
`req-ci` (`met`/`missing`). The course-versus-leadership cases were not in
this list. The assessment was not revised and no second model was called.

## Retrieval measured separately (Phase 13D)

The live run above returned `missing` for six requirements labelled `met`. That
number could not be read, because the report did not say whether the supporting
passage was ever in the prompt. Retrieval is now measured on its own.

Before the change, candidate evidence reached the assessor only when a claim
shared a keyword with the requirement or cleared the similarity floor. Measured
on 2026-09-22 against the same pilot, with no embeddings supplied:

| Quantity | Gated retrieval | Ranked shortlist |
|---|---|---|
| Scoreable requirements | 24 | 24 |
| Decided with no assessor call | 7 | 0 |
| Labelled supporting passages never shown | 2 | 0 |

The two passages were `dev-paraphrase` / `req-dba` and `heldout-paraphrase` /
`req-ci` — the same paraphrase cases that failed the live run. A paraphrase
shares no keywords and sat under the floor, so the requirement was decided
before the model saw anything, and no prompt change could have fixed it. The
seven uncalled requirements were being decided by the superseded lexical path.

The floor now ranks evidence rather than gating it: the five best claims and
their neighbours go to the assessor, and a requirement with no eligible claims
is recorded rather than handed back to the old rules. Candidate sets on this
pilot are one to two claims, so the call budget is unchanged.

The hermetic baseline is unaffected — it has no separate retrieval step — and
still shows 7 disagreements, 5 unsupported `met` and 0 order disagreements.

*Superseded — measured in the next section.* When this was written, the live
Ollama run had not been repeated since this change. The 9 disagreements, 1 unsupported `met` and 1 order disagreement
recorded above are still the last observed live numbers.

## Local Ollama, retrieval fixed (Phase 13D.6)

Measured on 2026-09-22, same pilot, same labels, `llama3.2` and
`nomic-embed-text` on `http://127.0.0.1:11434`, no API key, every call
`left_machine` false. Prompt version `evidence-assessment-v1`.

| Quantity | Hermetic | Live, gated retrieval | Live, ranked retrieval |
|---|---|---|---|
| Roles | 20 | 20 | 20 |
| Completion calls | 0 | 14 | 19 |
| Assessment disagreements | 7 | 9 | 15 |
| Labelled non-`met` returned as `met` | 5 | 1 | 0 |
| Pairwise order disagreements | 0 | 1 | 2 |
| Retrieval misses | not measured | not measured | 0 |
| Per-role latency p50 / p95 | — | 1.72s / 3.93s | 1.90s / 2.36s |

Retrieval is no longer the explanation: every labelled supporting passage
reached the assessor and every scoreable requirement was assessed. The
remaining errors are the model's, and they run in both directions at once.

Seven labelled `met` requirements came back `missing` — `role-strong`
`req-dbt` and `req-sql`, `role-partial` `req-dbt-partial`, `dev-duplicate`
`req-sql-a` and `req-sql-b`, `dev-injection` `req-dbt-inj` and
`heldout-paraphrase` `req-ci`. Two more were under-credited: `dev-paraphrase`
`req-dba` and `role-partial` `req-reliability`. Not one labelled `met` came
back as `met`. Six labelled `missing` requirements came back `partial` with a
cited span, including `heldout-poor` `req-fpga` and `role-poor` `req-ros`,
which share no subject matter with the evidence at all, plus the negation,
duration and aspiration cases.

The ranking follows from that: `role-strong` and `role-partial` both scored
zero and `role-poor` scored 25, so the two order constraints in `dev-ordering`
both failed.

**This run does not replace the hermetic baseline.** Unsupported `met` reached
zero only because the model returned `met` for nothing at all, which is not the
same as judging correctly. On the agreed rule, the assessment is revised rather
than given more calls: `evidence-assessment-v2` states a criterion for each of
the three levels, names an aspiration or a denial as `missing`, and says
`partial` is not the answer to being unsure. The completion model is now an
environment variable, so the same labels can be run against a stronger local
model without changing the prompt.

*Superseded — `evidence-assessment-v2` is measured in the next section.*

## Local Ollama, two models on the same labels (Phase 13D.6)

Measured on 2026-09-22, same pilot, same labels, same prompt
(`evidence-assessment-v2`), embeddings `nomic-embed-text` throughout, no API
key, every call `left_machine` false. Only the completion model changed.

| Quantity | Hermetic | llama3.2 | qwen2.5:7b | Gate |
|---|---|---|---|---|
| Assessment disagreements (of 24) | 7 | 12 | 3 | — |
| Labelled non-`met` returned as `met` | 5 | 4 | 1 | 0 |
| Pairwise order disagreements | 0 | 3 | 1 | — |
| Held-out order agreement | 1.0 | below 1.0 | 1.0 | 1.0 |
| Retrieval misses | not measured | 0 | 0 | — |
| Completion calls per role | 0 | 0.95 | 0.95 | 12 |
| Per-role latency p50 / p95 | — | 2.04s / 4.33s | 4.46s / 8.62s | 180s / 300s |

`qwen2.5:7b` passes every predeclared gate except one: unsupported `met` must be
zero and it returned one. That case is `dev-contradiction` / `req-k8s-conflict`,
where two cited passages disagree and the model answered `met` without setting
the contradiction flag. Its other two errors are `role-strong` / `req-sql` and
`role-partial` / `req-reliability`, both under-credited, and the single order
error is the tie that follows from the first. All three sit in the development
split; the held-out split had no disagreements.

`llama3.2` does not meet the bar and the failure is not only accuracy. Under
the defined levels it stopped refusing everything and started crediting
unrelated evidence as `met`, including `dev-injection` / `req-inject` — the
case where the untrusted text asks to be treated as a match. A 3B model was
given a judgement it cannot make, and the safe-looking zero unsupported `met`
in the previous run was only the same model refusing everything.

**Conclusion recorded against the agreed rule:** the structured assessment beats
the hermetic baseline on disagreements and unsupported `met` when the completion
model is capable, and loses to it when the model is not. The model is therefore
part of the contract, not a deployment preference, and the local default moves
to `qwen2.5:7b`.

The one gate failure gets one targeted change. `evidence-assessment-v3` states
the conflict rule as a rule of its own — two cited passages that disagree set
the contradiction flag and cannot be answered `met` — instead of trailing the
closing paragraph where the capable model missed it. The held-out split is the
check on that: it had no disagreements on v2, so a v3 that disturbs it is
overfitting to the three development cases and is reverted.

Measured on 2026-09-22, `evidence-assessment-v3` with `qwen2.5:7b` returned the
same three disagreements, the same unsupported `met` and the same order error as
v2. Stating the conflict rule more plainly changed nothing, and the printed
reason said why: *"The evidence shows the candidate operated Kubernetes in
production for three years, which meets the requirement."* The model was not
ignoring the conflict. It never saw it — `dev-contradiction` puts the denial in
a cover letter, and self-authored claims were excluded from retrieval because
they cannot support a match.

### Showing the cover letter was tried and reverted

`evidence-assessment-v4` showed up to two self-authored claims as context marked
`source=self-authored-cannot-support`, with their spans kept out of the
allowlist. Measured on the same labels with `qwen2.5:7b`, disagreements went
from 3 to 6 and the contradiction case was still not `partial`:

| Case | v3 | v4 | Reason printed on v4 |
|---|---|---|---|
| `dev-letter-dup` / `req-k8s` | met | missing | *(empty)* |
| `dev-contradiction` / `req-k8s-conflict` | met | missing | *(empty)* |
| `dev-overlap` / `req-java-years` | partial | missing | totals six years, not stated as continuous |
| `dev-injection` / `req-inject` | missing | met | matched the only evidence present |

The two empty reasons are the finding. An empty justification means the
assessment was rejected in validation and recorded as incomplete, and both cases
are ones where the letter repeats or denies a CV line: the model was shown the
letter, cited it, and lost the whole assessment because that span is not
citable. Showing evidence that may not be cited converts a wrong answer into no
answer. `dev-letter-dup` was correct on v3 and broke on v4, so the change cost
more than the case it was written for.

v4 is reverted. `dev-contradiction` stays a recorded gate failure: a denial that
lives only in a cover letter is not visible to the assessment, and closing that
needs a contradiction check the server performs itself, not a larger prompt.

### The two remaining disagreements are label questions

Neither is changed to match the model. Both are recorded so the decision is made
once, by a person, and written down.

- `role-strong` / `req-sql`. The requirement is "Write SQL for a cloud
  warehouse"; the evidence is "Wrote SQL reports for the warehouse team". The
  model would not infer *cloud* and answered `missing`. The label says `met`.
- `role-partial` / `req-reliability`. The requirement is "Owned the warehouse
  reliability programme"; the evidence is the same SQL-reports line. The model
  wrote that the evidence "is about building SQL reports and dbt models, but it
  does not show ownership of the warehouse reliability programme" — which is the
  definition of `partial` — and then answered `missing`. The label says
  `partial`.

### Run-to-run variation

`dev-overlap` and `dev-injection` changed between v3 and v4 without any code
touching them, so single runs do not separate a small difference from model
variation. The two dropped assessments have a structural explanation and the
label questions reproduce across every run; the rest of a 3-versus-6 gap does
not, on one run each. Configurations are compared here on one observed run
apiece and that is stated rather than averaged away.

**Current position:** `evidence-assessment-v3` with `qwen2.5:7b` is the last
measured configuration — 3 disagreements of 24, held-out split clean, every
predeclared gate met except unsupported `met`, which is the contradiction case
above. On 2026-09-22 the assessor prompt moved to `evidence-assessment-v5` with
domain exclusion of location/headline/title-only citations; that change is not
yet remeasured on the pilot set. The 2026-09-24 changes — positive CV evidence,
the 0.35 retrieval abstain, batched requirement classification and rejected
duplicate CV labels — are also unmeasured. Requirement precision, requirement
recall and mapping accuracy remain `TBD`.

## Known measurement limits

- The fixture set is synthetic and small. It detects regressions; it does not prove
  general accuracy.
- Requirement labelling is a judgement call. The labels are one reviewer's reading.
- Each provider is measured separately and never averaged with another. An average
  across providers describes a system nobody is running.
- The groundedness validator has false positives — a legitimately rephrased figure, a
  company name in a new inflection. They surface as template fallbacks, which is the
  safe direction to be wrong in, and the rate is published rather than tuned away.
