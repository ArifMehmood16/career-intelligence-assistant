# Implementation Plan: Apache 2.0 with project creator credit

**Actual Git branch**: `docs/phase-19-noncommercial-license` | **Date**: 2026-10-08
**Spec**: [spec.md](spec.md)
Root: [Licensing policy](../../PLAN.md#licensing-policy--2026-10-08).

## Summary and technical context

The human prioritises open-source collaboration and creator recognition. Adopt
unchanged Apache License 2.0 and a separate informational NOTICE naming Arif
Mehmood as original project creator. Add a visible README byline and align current
contribution/licensing guidance. Commercial use, paid services and closed-source
modifications are allowed subject to standard Apache terms; no permission gate.
No runtime, package metadata, database, dependency or infrastructure changes.

## Constitution check — before and after design

Pass: bounded human-authorized policy change; architecture/providers/privacy
unchanged. No executable tests pretending to prove legal enforceability. Preserve
and exclude the unrelated npm lock change. Reuse existing spec 012/PR #49/branch;
latest human direction supersedes the previous restrictive policy checkpoints.

## Structure and decisions

LICENSE: byte-identical official Apache 2.0. NOTICE: original copyright, project
creator and URL, informational licence/third-party scope. README: creator byline
and concise licence summary. CONTRIBUTING: Apache section 5 incoming terms and
retained copyright, no assignment/extra CLA. docs/licensing.md: permitted reuse,
standard notice options and limits of creator recognition. Preserve historical
logs; current PLAN/BACKLOG/spec reflect final scope. No new data model or API.

## Execution

Revise spec/plan/research/tasks and perform read-only consistency review. Download
and compare official bytes; replace current licensing documents. Review commercial,
closed-source, attribution/patent/contribution terms and independent-idea limits.
Check links/whitespace, third-party bytes, lock hash and intended staged scope.
Commit/push/update existing PR #49, observe new-head CI; do not merge.
