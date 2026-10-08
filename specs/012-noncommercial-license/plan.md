# Implementation Plan: Noncommercial reuse and collaboration

**Actual Git branch**: `docs/phase-19-noncommercial-license` | **Date**: 2026-10-08
**Spec**: [spec.md](spec.md)
Root: [Licensing policy](../../PLAN.md#licensing-policy--2026-10-08).

## Summary and technical context

Replace the existing proprietary no-reuse root LICENSE with a custom noncommercial
copyright licence. Update README and add CONTRIBUTING.md. No application code,
package metadata, schema, dependency, runtime or infrastructure changes are needed.
Documentation-only checks: scenario review, local links, whitespace, third-party
byte comparison and explicit staged-file review. No automated legal validity claim.

## Constitution check — before and after design

Pass: bounded human-authorized documentation scope; existing architecture,
providers, privacy and domain invariants unchanged. No private uploads or secrets.
No new tests mirror legal wording: executable tests cannot validate enforceability.
Preserve the unrelated working-tree npm lock change and exclude it from commits.
The Spec Kit scripts' logical feature name differs from the actual Git branch;
feature.json selects this feature without creating a second branch.

## Structure and decisions

LICENSE is authoritative; README is a concise linked summary. CONTRIBUTING.md
states incoming same-licence terms without copyright transfer or automatic
commercial grants. Root PLAN/BACKLOG and AI/journal records link this bounded scope.
Feature artifacts record design and validation, not another roadmap.
Third-party fonts and Spec Kit MIT notices remain untouched. Runtime API contracts
and data models do not change; no new contract or source directory is warranted.

## Execution

Research existing ownership and primary licensing guidance; write requirements,
plan/tasks and perform read-only consistency review before implementation. Draft
licence and summaries; review every US1/US2 edge case and all requirement coverage.
Check links/whitespace and third-party bytes; update factual logs and root acceptance,
then commit only intended files. Follow existing human authorization to deliver via
one new PR because PR #48 is merged. The human owns merge and legal acceptance.
