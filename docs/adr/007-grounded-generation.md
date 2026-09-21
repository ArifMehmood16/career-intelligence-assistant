# ADR 007 — Generated drafts may only assert what cited spans contain

- Status: accepted
- Date: 2026-09-18

## Context

The product generates text a user will put their name on: CV bullets, an interview
preparation pack, a cover letter. This is where a language model is most useful and
most dangerous. A fluent draft that adds a number, a technology or a duration the
candidate never claimed is worse than no draft — it is a fabrication the candidate
carries into an interview.

ADR 004 keeps the model out of scoring. This extends the same principle to generated
prose, which otherwise becomes the back door through which unverified claims reach
the user.

## Decision

Every generated artefact is bound to the spans it cites, and the binding is enforced
in code rather than in the prompt.

1. **Inputs are spans, not free text.** A draft is generated from the claims and
   requirements already extracted and stored, each carrying span identifiers.
2. **The model is given a phrasing job.** It restructures supplied text. It is not
   asked what the candidate has done.
3. **A validator runs on every draft before it leaves the server.** Every number,
   date, duration, percentage, employer, product and technology token in the draft
   must appear in the cited spans after normalisation. A draft that fails is
   regenerated once; a second failure falls back to deterministic template output.
4. **Every artefact carries provenance**: provider, model, whether content left the
   machine, whether the validator passed, and whether a fallback was used.
5. **There is always a hermetic path.** With no model configured, drafts are still
   produced from templates over the same claims. The feature does not require a model
   to exist; the model only makes it read better.
6. **Refusal is a supported outcome.** The cover letter refuses when fewer than two
   must-have requirements are met, and says why.
7. **HTTP uses this path.** Bullet, interview-pack and cover-letter routes call
   `generate_draft`. The SQL draft adapter persists the validator's real verdict and
   never rewrites `FAIL` to `PASS`. Tone and honest-gap-line inputs change the
   template that enters the pipeline. A bullet with no cited claim is refused, not
   stored. The route map is `docs/production-wiring.md`.

## Consequences

- Drafts are blunter than an unconstrained model would produce. That is the trade
  being made, and it is the right way round for a document a person signs.
- The groundedness violation rate becomes a measurable quantity, reported per provider
  in `docs/evaluation.md` alongside quality, latency and cost.
- The validator is itself a piece of engineering with false positives — a legitimately
  rephrased number, a company name in a new inflection. It is tuned against the
  evaluation dataset, and its failures are visible in the fallback counter rather than
  silent.
- The feature set can grow without weakening the invariant: any future generated
  artefact passes the same validator or it does not ship.

## Alternatives considered

- **Prompt instructions only** ("only use facts from the CV"). Rejected: unenforceable
  and untestable. A prompt is a request; the invariant needs a check.
- **Show the model's output with a warning banner.** Rejected: it moves the burden of
  verification onto the person least able to carry it at the moment they are least
  likely to.
- **No generated prose at all.** Rejected: the gap plan alone leaves the most useful
  half of the product unbuilt, and the constraint is what makes the generated half
  defensible.
