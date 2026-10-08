# Implementation Plan: Adopt unchanged PolyForm Noncommercial

**Actual Git branch**: `docs/phase-19-noncommercial-license` | **Date**: 2026-10-08
**Spec**: [spec.md](spec.md)
Root: [Licensing policy](../../PLAN.md#licensing-policy--2026-10-08).

## Summary and technical context

The human selected the reusable licence after custom draft f1d1f4e. Download
PolyForm Noncommercial 1.0.0's official plain text and copy it unchanged to LICENSE.
Keep Arif's Required Notice separately in NOTICE; explain commercial licensing and
ownership in docs/licensing.md, README and CONTRIBUTING, without adding extra terms.
No runtime, package metadata, database, dependency or infrastructure changes.

## Constitution check — before and after design

Pass: bounded human-authorized licensing scope; architecture, providers and privacy
unchanged. No new code or tests pretending to prove legal enforceability. Exclude
and preserve the unrelated npm lock modification. Reuse spec 012 and existing PR
#49; human selection supersedes the initial stricter custom requirements.

## Structure and decisions

LICENSE: byte-identical official text. NOTICE: Required Notice and third-party
scope. README: concise standard-licence summary and commercial licensing link.
CONTRIBUTING: incoming same-licence terms, retained contributor rights and no silent
commercial grant. docs/licensing.md: explanatory guide, not another licence or a
revenue contract. No automatic ownership of contributors' work or revenue seizure.
Root PLAN/BACKLOG and factual logs reconcile final scope; earlier custom draft is
historical. No data model, API contract or new source directory is needed.

## Execution

Revise spec/plan/tasks to the human choice; read-only consistency review, then
replace licence and summaries. Compare official bytes, review owner/revenue and
organisational exceptions, check links/whitespace and third-party bytes. Commit
explicit files, push/update existing PR #49 and observe new-head CI; do not merge.
Do not draft a commercial agreement without defined parties and negotiated terms.
