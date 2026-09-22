# ADR 010 — Model-first extraction with server-verified quotes

- Status: accepted
- Date: 2026-09-21
- Plan: 13C.10

## Context

Phases 5 and 6 shipped a model-backed extractor that did not extract. It ran the
rules extractor first, then discarded every model item whose text was not already
in the rules output. Competency, seniority and spans came from the regex. The
model could only remove what the regex had found; it could never find what the
regex missed.

Hermetic adapters were also the *product* default, not only the test fixture.
A running instance with no extra configuration analysed real documents with a
bullet regex and a twelve-keyword competency list.

On 2026-09-21 the maintainer ran a real CV and a real job advert through that
pipeline. Observed:

- The claim extractor produced **zero claims**. `pypdf` emits bullets as `•Text`
  with no following space; normalisation rewrites that to `-Text`; the bullet
  pattern required whitespace after the glyph. Every requirement mapped to
  `missing` and the fit score was 0.
- With that one character corrected it produced **4 claims out of roughly 14**,
  all from the first role. `_SECTION_STOP` matched a wrapped line that happened
  to begin with the word "education", ending experience parsing at the second
  job.
- Every claim came out `undated`, because `pypdf` puts role dates on the role
  line and the parser expected them on a line of their own.
- The advert produced **18 requirements, all must-have, all competency
  `general`**, including the salary band, share options, the remote-working
  policy, the right-to-work line, and the three bullets under *What this role
  is not*.
- With claims present the mapping then reported **11 met, 7 partial** — asserting
  the candidate *meets* "£70,000 - £80,000 depending on experience".

The scoring layer was never the problem. Deterministic, explainable scoring is
the one thing a reviewer has not seen elsewhere. What failed is everything
upstream of it: deciding what counts as a requirement is a language task, and a
hermetic test fixture should never have been what a real user hits.

`EXTRACTION_STRATEGY` was written in `config/app.env` and read nowhere in
`backend/src`. Extractor routing is decided in `selected.py` by provider id
alone.

## Decision

**The model extracts. The server verifies the quote. The domain decides.**

1. A running instance defaults to a local Ollama model for completion and
   embeddings. Hermetic remains the fixture `make test` selects so the suite
   stays offline. It is not a deployment option.
2. Requirement extraction returns, per item: a verbatim `quote`, an `item_type`
   (`requirement`, `responsibility`, `benefit`, `logistics`, `non_requirement`),
   must vs desirable, and a competency from an open vocabulary. The server
   locates the quote in the stored normalised text and builds the span from
   those offsets. Anything that does not verify is dropped and counted — never
   repaired, never fuzzy-matched. Only `requirement` and `responsibility` items
   reach `map_requirements`.
3. CV extraction returns roles (employer, title, date-range quote) and claims
   beneath them (quote, competency, scope, technologies, outcome). Dates are
   parsed in domain code; the model never supplies recency or duration. Every
   role is extracted, not only the first.
4. An uploaded cover letter is extracted into the same claim shape and flagged
   `self_authored`. `map_requirements` ignores those claims. They stay citable
   for Ask; they cannot move a fit score.
5. The rules extractors remain, repaired against the three PDF shapes the audit
   found, so the hermetic fixture is honest. They are not the product default.

`EXTRACTION_STRATEGY` is deleted. Provider id already carries the decision.

## Consequences

- A prose advert the regex cannot parse can still produce requirements, provided
  every quote appears in the stored text.
- A salary band, a benefit or a "this role is not" bullet can be extracted and
  shown, and can never be scored.
- Fabrication is bounded by verbatim locating, not by intersecting with a regex.
  Prompt injection in a job description still cannot invent a requirement the
  document does not contain. Quoting an instruction that *is* in the document is
  possible; classification and scoring, not verification, have to deal with that.
- `make test` is unchanged: the test app factory still builds a hermetic app.
- Persistence of `item_type` and `self_authored` landed in 13C.6 so a SQL
  reload preserves those flags.
- Three-signal matching (13C.5) combines lexical overlap, embedding cosine and
  model adjudication of XOR disagreements in domain code. Hermetic analysis
  skips the adjudicator and keeps the OR of the first two.
- Output depth (13C.8) is shipped: a prose fit summary on GET `/roles/{id}`,
  full quoted CV evidence on each requirement, and interview prompts that
  quote the candidate's own claims.
- [ADR 011](011-evidence-assessment-contract.md) supersedes consequence 4 for
  scoring: concrete experience in an uploaded letter can count, with its source
  shown and duplicates removed. An aspiration does not count, and a generated
  draft never raises the score. The extractor still flags uploaded letters
  `self_authored`; the running matcher still ignores them until 13D.5.
- Pay and logistics are classified by the extraction prompt and JSON schema,
  not by a post-filter. The local Ollama adapter sends that schema as
  `format` so the enum descriptions reach the model.
- An extract with no scoreable items is banded `unscored`, not `limited`.
- ADR 003's "hermetic default" referred to the test fixture and, incorrectly, to
  the running product. The product default is now a local model; see the
  amendment there.

## Rejected alternatives

- **Keep the regex as default and "improve the patterns."** The audit is the
  evidence. A wrapped line beginning with a section word, a date on the role
  line, and a salary band classified as a must-have are not one-off bugs; they
  are what a regex does to real documents.
- **Trust the model without a verbatim quote.** That would let model output
  reach the user without a span check, which AGENTS.md forbids as an
  architectural change.
- **Fuzzy-match a near-miss quote back into the document.** PLAN 5.4: drop it,
  count it, never repair it. A repaired quote is a fabricated span.
- **Implement `EXTRACTION_STRATEGY` as a second switch.** It was set in config
  and read nowhere. Provider id already decides which extractor is constructed.
- **Drop unscoreable items at extraction time.** Salary, location and "this role
  is not" are real content a reader wants. They are kept and shown; they are
  simply never mapped.

## Amendment — 2026-09-22 (13D.6c)

The quote-copying contract dropped real requirements when the model omitted
Markdown markers, and it kept generic headings that the model copied exactly.
That is amended as follows. The original decision stays as the record of what
13C shipped.

The server segments the stored normalised text into stable spans before the
model runs. A non-empty line is one span. A line with more than one sentence
is one span per sentence, so unrelated requirements on one line are not
merged. The server does not split a single sentence further. Each span has a
server-issued id and the exact stored text.

The model classifies those ids. It does not supply the evidence text. Unknown
ids, duplicated ids and ids from another document are rejected. Every server
span needs exactly one accepted classification; otherwise the extraction is
incomplete and no fit score is published. The job fails with
`extraction_incomplete`. There is no fuzzy quote match and no fallback to the
rules extractor for a partial model response.

A line that is only a section introduction, ending in a colon, is
`non_requirement` even if the model calls it a responsibility. Benefits and
logistics stay unscoreable kinds. CV claim extraction is the same principle
and is 13D.6d, not this amendment.
