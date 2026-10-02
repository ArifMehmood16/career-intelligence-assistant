# Known limitations

Written down rather than papered over:

- English-language CVs and job descriptions only.
- PDF and DOCX input; scanned image CVs are out of scope until OCR is justified.
- One CV per workspace at a time. Multi-CV comparison is a later candidate.
- Supporting cover letters may be uploaded, queried and cited, but are excluded from
  claims, mappings and fit scores. A denial that appears only in a cover letter is
  therefore invisible to the assessment.
- Historical measurements refer to the retired analysis. Current single-call
  chunking/judging quality and live latency have not yet been measured.
- Analysis runs on an in-process job queue over PostgreSQL. A distributed queue is not
  pretended here.
- The Settings screen still lists the hermetic test fixture as a provider (see
  [BACKLOG.md](../BACKLOG.md)).
- Generated drafts are drafts. The product does not edit your CV or submit
  applications, email or messages. Enabled hosted providers receive analysis and
  generation inputs through the [egress gate](model-providers.md).
- No employer-side use. This is a candidate tool; screening applicants with it would
  need bias evaluation and a fairness review that is not in scope.
- No authentication or multi-tenancy. Workspace scoping is enforced and tested, but
  the identity behind it is a cookie. Required before any untrusted user touches it.

- The agent's tool steps in Ask are shown for answers given in the current session;
  they are not stored, so a reloaded conversation does not show them.

## With more time

Current priorities are in [BACKLOG.md](../BACKLOG.md): verify the consolidation and
migration on disposable data, run one browser journey, measure frozen-label quality
and cold/warm latency, then finish startup/security release checks. Tests/lint for
final edits were deferred at the human's request.
