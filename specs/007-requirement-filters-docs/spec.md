# Requirement filters and current architecture documentation

Created 2026-10-05. Branch: fix/phase-19-analysis-usability. Human-authorized group
following the 19.3 runtime fix; [PLAN 19.1](../../PLAN.md#191--retire-the-competing-analysis)
and [BACKLOG](../../BACKLOG.md#now--verify-one-working-architecture).

## User scenarios

### US1 — Focus the finished requirements list (P1)

Filter requirements by Met/Partial/Missing and score together. Show how many
requirements remain, distinguish no matching filters from no requirements, and
clear filters. Preserve the published overall fit, evidence and retrieval traces.
Score filtering uses the server's requirementScore as a whole percentage; null
remains Not scored, never zero. Default: all requirements in the existing order.
Acceptable ranges: 0–24, 25–49, 50–74 and 75–100 percent, plus Not scored.
A human clarification on the visible 0–4 Match rating takes precedence if received.

### US2 — Read accurate architecture and see the current UI (P2)

README and architecture diagrams describe the running chunk/search/judge system,
SQL-backed jobs, bounded I/O, spawned parsing, safe expiry, domain arithmetic and
shared published views. Screenshots use current rendered synthetic gallery data,
not personal CV/JD content. Clearly label screenshot provenance.

## Requirements and acceptance

- FR-001: Combine status and score filters using existing validated fields; never
  recalculate fit or call a provider. Default shows all, including unscored items.
- FR-002: Accessible named controls, shown/total count, clear action and distinct
  filtered-empty state. Hide controls when analysis is loading/error/incomplete.
- FR-003: Preserve evidence/trace actions, original ordering and server overall fit;
  reset list filters for a new analysis publication.
- FR-004: Update README, docs/architecture.md, docs/how-to-use.md, current technical
  diagrams and screenshots using observed source and synthetic browser rendering.
- FR-005: Continue on the current branch at the human's request. Commit green steps,
  push them to the normal checkout's remote and remove only preserved redundant refs.

## Success criteria

Synthetic component tests cover combined filters, zero/null, reset and unchanged
fit; frontend lint/typechecks and full hermetic checks pass. Browser verifies actual
filter interactions and screenshots. Diagrams match inspected production wiring.
No migrations, new dependencies, paid model calls, personal screenshots or broad
release claims. Existing current-analysis APIs and scoring semantics stay intact.
