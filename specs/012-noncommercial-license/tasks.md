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

## Human-selected standard licence continuation — 2026-10-08

The original T001–T006 record the custom draft checkpoint. The human subsequently
selected unchanged PolyForm; final requirements in spec.md supersede the earlier
blanket commercial restrictions and align to the standard permitted purposes.

- [x] T007 Review unchanged official PolyForm and ownership/revenue limits; revise
  spec.md, plan.md and research.md and perform consistency review (FR-001–FR-006).
- [x] T008 [US1] Copy official text unchanged to LICENSE and add owner's Required
  Notice in NOTICE, preserving third-party notices (FR-001/FR-002/FR-004).
- [x] T009 [US2] Align README.md, CONTRIBUTING.md and docs/licensing.md with standard
  exceptions, retained copyright and negotiated commercial fees/revenue share;
  assert no automatic revenue entitlement (FR-002–FR-005).
- [x] T010 Review official bytes/links/whitespace/third-party notices; reconcile
  PLAN.md/BACKLOG.md and factual AI/journal records, commit/push/update existing
  PR #49 with updated-head checks enforced and no merge (FR-006/SC-001–SC-003).

Execution: T007 -> T008 -> T009 -> T010, one branch/PR and no parallel agents.

Observed standard continuation: official text is byte-identical, four existing
third-party notices unchanged and 71 local links resolve. Required Notice and
ownership/revenue guidance reviewed; no automatic royalty or custom extra licence
terms. Update the existing PR and observe CI on the pushed head before merge.

## Revised internal-use policy continuation — 2026-10-08

T001–T010 remain historical checkpoints. The latest human policy expressly allows
internal business use and closed-source modifications; current spec.md supersedes
the earlier restrictions. Continue on the same branch and PR #49.

- [x] T011 Review latest policy/primary sources, revise spec/plan/research/validation
  guide and perform read-only consistency analysis (FR-001–FR-006).
- [x] T012 [US1] Write custom named terms with internal business and closed-source
  permissions and external monetisation conditions (FR-001/FR-002).
- [x] T013 [US2] Preserve ownership, prior grants and third-party boundaries;
  reserve separately negotiated external monetisation rights (FR-002/FR-004).
- [x] T014 [US3] Align attribution, NOTICE, README, contributor/licensing guidance,
  PLAN/BACKLOG and factual logs (FR-003–FR-005).
- [x] T015 Review eight scenarios, links, whitespace, third-party bytes and scoped
  diff; record observed local evidence and preserve the unrelated lockfile (FR-006,
  SC-001–SC-003).

Execution: T011 -> T012 -> T013 -> T014 -> T015. No new branch, PR or subagents.

Observed revised-policy review: personal learning and free unmonetised public use
are granted in section 2; internal business use in sections 1–2; closed-source
changes in section 2. Sales, subscriptions/paid services and ads/sponsorship are
reserved by sections 1 and 3. Section 4 prohibits removing original credit and
specifies accessible external attribution. Four third-party notices unchanged;
72 local Markdown links resolve and branch whitespace passes. No runtime changes.
Delivery: commit/push and update existing PR #49; observe CI on the updated head.
The PR records delivery/check results without predicting them in this local record.
