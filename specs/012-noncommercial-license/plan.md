# Implementation Plan: Permit internal use; reserve external monetisation

**Actual Git branch**: `docs/phase-19-noncommercial-license` | **Date**: 2026-10-08
**Spec**: [spec.md](spec.md)
Root: [Licensing policy](../../PLAN.md#licensing-policy--2026-10-08).

## Summary and technical context

The latest human policy permits internal business use and closed-source changes,
which unchanged PolyForm Noncommercial does not expressly provide for all
businesses. Write independently named custom terms and replace current summaries.
Allow learning, internal business operations and free unmonetised public products;
reserve external monetisation for prior written permission. Define attribution in
copies, external products and accompanying public documentation.
No runtime, package metadata, database, dependency or infrastructure changes.

## Constitution check — before and after design

Pass: bounded human-authorized licensing scope; architecture, providers and privacy
unchanged. No executable tests claiming to prove legal enforceability. Preserve
and exclude the unrelated npm lock change. Reuse spec 012 and existing PR #49;
latest human direction supersedes both earlier unmerged policy checkpoints.

## Structure and decisions

LICENSE: independently written custom source-available terms, explicit internal
permission and external monetisation boundary, attribution, rights limitations and
warranty disclaimer. NOTICE: owner identity and third-party scope. README: concise
permissions and guide link. CONTRIBUTING: same-licence submissions without copyright
assignment or an additional external monetisation grant. docs/licensing.md:
concrete allowed/restricted examples, attribution, ownership and negotiated fees.
Keep historical log entries; current PLAN/BACKLOG/spec acceptance reflects the
latest policy. No data model, API contract or new source directory is needed.

## Execution

Revise spec/plan/tasks/research; perform read-only consistency review before editing
licence documents. Review eight human scenarios, internal paid-worker/client-service
boundary, attribution, closed-source rights and valid earlier grants. Check links,
whitespace, third-party bytes and explicit staged scope. Commit/push/update existing
PR #49 and observe updated-head CI. Do not merge or create a commercial contract.
