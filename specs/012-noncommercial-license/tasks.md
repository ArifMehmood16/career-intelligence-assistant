# Tasks: Noncommercial reuse and collaboration

Root: [Licensing policy](../../PLAN.md#licensing-policy--2026-10-08).
Spec: [spec.md](spec.md). Documentation-only, one actual Git branch and PR.

## Setup and foundation

- [x] T001 Inspect LICENSE/README, ownership, third-party notices and clean main;
  record primary-source decisions in research.md (FR-004/FR-006).
- [x] T002 Write spec.md, plan.md and validation guide; perform read-only consistency
  and constitution review before implementation (FR-001–FR-006).

## US1/US2 — Noncommercial reuse and permission boundary

- [x] T003 [US1] Replace LICENSE with allowed use/attribution conditions and preserved
  third-party/statutory boundaries (FR-001/FR-004).
- [x] T004 [US2] Cover direct/indirect commercial advantage, modified copies,
  payments/favors, no-fee business use and explicit written exceptions in LICENSE
  (FR-002/FR-003).

## US3 — Contribution and current summaries

- [x] T005 [US3] Update README.md and add CONTRIBUTING.md with retained ownership,
  incoming same-licence terms and no automatic commercial grant (FR-004/FR-005).

## Verification and delivery

- [x] T006 Review scenarios, links, whitespace and third-party bytes; update PLAN.md,
  BACKLOG.md, AI_DEVELOPMENT_LOG.md and docs/engineering-journal.md from evidence,
  then commit explicit files and update spec status (FR-006/SC-001–SC-003).

## Dependencies and execution strategy

T001 -> T002 -> T003/T004 -> T005 -> T006. T003 and T004 share LICENSE and remain
sequential. README and contributor proofreading are independent after the licence
is settled; no subagents are needed. Deliver one licensing concern, not runtime work.

Observed local review: allowed/restricted scenarios have express licence terms,
all four tracked third-party notices are unchanged, and local file links resolve.
No automated legal-enforceability claim or runtime change. Unrelated npm lock
working copy remains excluded. Exact commands/checks are in the engineering journal.
