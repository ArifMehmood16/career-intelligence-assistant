# Known limitations

Written down rather than papered over:

- English-language CVs and job descriptions only.
- PDF and DOCX input; scanned image CVs are out of scope until OCR is justified.
- One CV per workspace at a time. Multi-CV comparison is a later candidate.
- Supporting cover letters may be uploaded, queried and cited, but are excluded from
  claims, mappings and fit scores. A denial that appears only in a cover letter is
  therefore invisible to the assessment.
- Accuracy is measured on one small synthetic pilot, one run per configuration. The
  running assessor prompt (`evidence-assessment-v5`) has not been remeasured yet.
- Analysis runs on an in-process job queue over PostgreSQL. A distributed queue is not
  pretended here.
- The Settings screen still lists the hermetic test fixture as a provider (see
  [BACKLOG.md](../BACKLOG.md)).
- Generated drafts are drafts. The product does not edit your CV, and does not send
  anything anywhere.
- No employer-side use. This is a candidate tool; screening applicants with it would
  need bias evaluation and a fairness review that is not in scope.
- No authentication or multi-tenancy. Workspace scoping is enforced and tested, but
  the identity behind it is a cookie. Required before any untrusted user touches it.

- A role analysed on pipeline v2 shows its fit and gaps from the verdicts, but its
  Prepare and Letter tabs, its fit summary and the ranking reasons still read the v1
  analysis, which it does not have, so they are empty. Pipeline v1 is the default.
- The agent's tool steps in Ask are shown for answers given in the current session;
  they are not stored, so a reloaded conversation does not show them.

## With more time

In order, from [BACKLOG.md](../BACKLOG.md): review and build the v2 architecture
(Phase 18) and measure it against v1 — the 13D.6g measurement becomes that
baseline — before v1 is retired. Then the rest of the release path: retention, rate
limiting and a recorded security scan (Phase 15), a durable audit trail
(15B.6–15B.10), and verified containers with a Playwright walkthrough (Phase 16).
