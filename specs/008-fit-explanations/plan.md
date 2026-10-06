# Implementation plan — fit explanations
Branch: feat/phase-19-fit-explanations; date 2026-10-06; [spec](spec.md).

## Summary
Reuse stored score components for normalized point attribution. Extend existing
chunk/judge contracts with verified qualitative experience expectations and an
untrusted whole-document context prefix. Keep domain aggregation unchanged.
Render immediate pending/answering Ask status using existing request state.

## Technical context
Python 3.14/FastAPI/SQLAlchemy/PostgreSQL and TypeScript/React/TanStack Query.
Existing pytest/Vitest; no new dependency. SQL JSON metadata/payloads support
additive expectation fields and old-row defaults without a migration. Read existing
published weights/contributions, never the current rubric for old results.

## Constitution check
One pipeline and pure domain arithmetic retained. Expectations/quotes verified;
whole context cannot introduce citation candidates. Hosted egress unchanged.
Bounded request capacity includes context; no extra completion wave. Candidate
contact chunks excluded. JSON reads remain backward compatible. Human explicitly
requested the scoring display and contextual judgment group ahead of release gates.
Checks reviewed before and after design: no violations.

## Source structure
backend/src/career_assistant/domain/{scoring_v2,chunking,judging,candidate_facts}.py
application/{contracts/chunking,chunking/mapping,chunking/prompts,judge/prompt,
judge/cache,analysis/v2,ports/v2_results}.py
adapters/persistence/{chunk_repos,v2_analysis_repos}.py; api/{schemas,routes_verdicts}.py
frontend/src/{components/ask,components/role/verdicts,api,types,routes/dev.states.tsx}

## Design
- Domain point shares normalize stored contribution and weight to 100. API exposes
  nullable scoreImpact with earned/possible/shortfall. Missing metadata stays null.
- experience_expected is an optional verbatim quote fragment, validated inside the
  requirement quote. Numeric tenure remains scoped. Seniority may be grounded in
  full advert/title, with applicability determined by extraction, never a blanket
  numeric inheritance. Prompt versions invalidate extraction/judge caches.
- CandidateFacts carries optional immutable JudgeDocumentContext built from stored
  non-contact CV chunks and the JD. render_facts includes it before packets; budget
  and cache include all visible context/facts. Same facts flow through rechecks.
- Existing numeric/rationale dimensions remain; qualitative anchors apply when
  years are absent. Wire fields expose verified expectations; card labels Asked
  and Supported, plus anchors selected for numeric/qualitative mode.
- ChatView shows a labelled spinner when sending; pre-event, answering, finalizing
  states are distinguishable. Container regressions hold response promises and
  cover terminal clearing/cancellation. New gallery states use props only.

## Delivery
Red/green each behavior, focused lint/typechecks and green commits; full lint/test
and disposable SQL integration; browser synthetic verification; docs/plan/log
update, push and review PR under existing human publication authorization.
