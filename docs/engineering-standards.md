# Engineering standards

Followed:

- TDD at behaviour boundaries: a failing test first, one green commit per cycle,
  refactors in their own commits ([AGENTS.md](../AGENTS.md#development-style)).
- Ports and adapters, SOLID and named design patterns, with an architecture guard test
  on the import direction.
- mypy strict, TypeScript strict, Ruff, ESLint and Prettier, an 80% branch-coverage
  gate on the backend, and SonarQube-clean coding rules.
- One contract suite every provider adapter passes; hermetic default tests with no
  key, model or network.
- Twelve ADRs, a threat model, a route-to-adapter wiring matrix, an engineering journal
  and a factual AI development log.
- Conventional commits on task branches, merged by pull request; CI runs lint,
  typecheck and the hermetic tests.

Skipped or not done yet, deliberately named:

- Authentication and multi-tenancy.
- Playwright end-to-end tests (16.5), verified containers (16.1), and a recorded
  passing `make security` run (15.1).
- Retention and rate limiting (15.2, 15.3); durable audit tables (15B.7).
- CI runs when a pull request is opened, not on later pushes, and SonarQube runs
  locally rather than in CI.

## How AI tools were used

Coding agents did most of the typing; the architecture, the invariant, the security
boundaries and every merge decision stayed with me. Cursor (Composer and Grok models)
wrote most of the implementation. Claude (Opus) brought the run-and-deploy surface
forward, started 13C with the local-model default and the fixture repairs, and ran the
13D measurement work. Codex reviewed the persistence design, audited the
production wiring after Phase 13 and refocused the plan for 13D. Lovable designed the
frontend. Every agent works to [AGENTS.md](../AGENTS.md), and each significant change has
an entry in [AI_DEVELOPMENT_LOG.md](../AI_DEVELOPMENT_LOG.md) recording what was accepted,
changed or rejected.

- **Rejected:** a log statement in every backend function (entry 111) — it would drown
  the signal and risk document text in logs; the analysis path got stage counts
  instead.
- **Rejected:** unpinned dependency ranges in the image and Ollama in the default
  Compose stack (entry 003).
- **Changed:** a suggestion to copy the private smoke-test CV into the repository as a
  fixture became a synthetic, public-safe fixture of the same shape (entry 108).
- **Reverted after measurement:** showing cover letters to the assessor doubled the
  disagreements on the labelled pilot (entry 101).
- **Lovable:** the design system and screens were kept; the fixture data layer, the
  editor telemetry and the branding were replaced (entry 008,
  [docs/frontend-integration.md](frontend-integration.md)).
