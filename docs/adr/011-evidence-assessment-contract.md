# ADR 011 — Evidence assessment is validated; the domain calculates the score

- Status: accepted
- Date: 2026-09-22
- Plan: 13D.2

## Context

Relatedness was being treated as sufficient evidence. Lexical overlap on a shared
word, or agreement between lexical and embedding signals, could mark a requirement
`met` with no check that the passage actually supports the stated scope, duration
or conditions. The 2026-09-22 hermetic baseline recorded that failure: an
introductory Python course was assessed as meeting "five years leading production
Python systems", and nine labelled non-`met` cases came back `met`.

A citation only proves that a span exists in a stored document. It does not prove
the span supports the requirement. Token overlap in a groundedness check has the
same limit.

Uploaded cover letters were excluded from scoring entirely (ADR 010). That is
stricter than the product needs, and it throws away concrete experience a
candidate has already written down. It does not, by itself, stop an aspiration
or a generated draft from being mistaken for evidence if a later change lets
that text into the mapping.

## Decision

Three roles, and they stay separate:

1. The model assesses retrieved evidence against the requirement's stated
   criteria. It does not emit a score and it does not hide its reasoning.
2. The server validates that assessment: types, allowed span ids, completeness
   and duplicates. A missing, refused or malformed assessment is recorded as
   incomplete and never becomes a match.
3. The domain calculates the score from the validated assessment and the
   existing rubric. A model number never becomes the fit score.

A citation proves where text came from. It does not prove that the text supports
the claim.

Letter policy, decided here:

- Concrete experience in an uploaded CV or an uploaded letter counts, with its
  source shown and duplicates removed.
- An aspiration does not count.
- A generated draft must never raise the score.
- Two copies of the same experience, including the same fact in the CV and in an
  uploaded letter, are one piece of evidence.

This decision supersedes the parts of ADRs 004, 009 and 010 that treated signal
agreement, or any resolvable citation, as proof of support, and the part of
ADR 010 that excluded every uploaded letter from the score. Those ADRs keep
their original text; the amendment is this page.

The running matcher still excludes self-authored claims. Implementing this
contract is 13D.3 through 13D.5, not this record.

## Amendment — 2026-09-22 (false Met citations)

Validated span ids are necessary but not sufficient. Location lines, contact
details, profile headlines and bare employer-title-date headings are not
evidential support: they are excluded from the assessor shortlist, and a `met`
or `partial` whose remaining cited claim bodies fail that check is recorded as
`missing`. Only the claim body span is offered as citable; attached role
headings stay provenance. Prompt version `evidence-assessment-v5` states that
rule to the model. The domain still calculates the score.

## Consequences

- Keyword overlap and embedding agreement retrieve evidence. They do not decide
  that a requirement is met.
- Fit, Gaps, Prepare and Letter must read one validated analysis. They do not
  re-decide support.
- Generated cover letters, bullets and interview packs stay outputs. Feeding one
  back in as a document cannot raise the score.
- Ask may still cite an uploaded letter. That citation remains provenance.
- Until 13D.5 lands, behaviour tests that exclude self-authored claims describe
  the code, not this contract.
