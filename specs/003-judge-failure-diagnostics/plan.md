# Implementation Plan: Explain incomplete judging

Branch: `fix/phase-19-judge-failure-diagnostics` | Date: 2026-10-02 | [Spec](spec.md)
Root: [PLAN 19.2](../../PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider)

## Summary

Log fixed transport failure categories/timeout phases before unchanged translation.
Log swallowed judge exceptions with phase/category/counts; log domain rejection
counts before repair and after it, plus aggregate incompleteness. Never log problem
strings, requirement IDs, prompts, replies, exception messages or causes.
Raise only the ignored local PROVIDER_TIMEOUT_SECONDS to 180; preserve retries/defaults.

## Technical Context

Existing Python 3.14/httpx/stdlib logging/pytest. No dependencies, DB, frontend or
API schema changes. Reuse log_failure/log_event and existing provider/model identity.
Unit regressions use MockTransport and ScriptedStructured, with no live calls.
This improves diagnosis; no latency/quality target is claimed from the mitigation.

## Constitution Check

Before and after design: current pipeline, egress and domain authority preserved.
Incomplete still prevents publication. No raw diagnostics or vendor logic in the
application. Tests/lint stay deferred; reviewed source is not a passed gate.
Baseline exception: aae9b24 contains the required consolidation/schema repairs;
use it instead of obsolete main, as in the preceding human-directed debugging task.

## Project Structure

Reuse adapters/providers/httpx_transport.py, application/judge/service.py and their
existing unit tests. Update docs/model-providers.md, docs/running-locally.md, root
PLAN/BACKLOG, AI log and engineering journal. Feature artifacts live here.

## Implementation Sequence

1. Author regressions, without running deferred checks.
2. Add diagnostics at existing catches/checks with numeric or fixed fields only.
3. Change ignored local timeout, inspect effective non-secret values, update docs.
4. Review full diff and commit; leave final verification pending.

## Complexity Tracking

No new abstraction, persistence or architecture; no unresolved design choice.
