# Implementation Plan: OpenAI analysis request repair

Branch: `fix/phase-19-openai-request-errors` | Date: 2026-10-02 | [Spec](spec.md)
Root: [PLAN 19.2](../../PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider)

## Summary

Repair the existing strict-schema converter: defaulted non-nullable arrays remain
arrays, all properties remain required, and explicitly nullable alternatives remain
without another null branch. Preserve original Pydantic/server validation.
Add one OpenAI-local response classifier, reused by completion, embedding and tool
calling, that emits allowlisted metadata before existing HTTP classification.

## Technical Context

Existing Python 3.14, Pydantic, httpx, pytest and logging. No dependencies, storage,
API schema, frontend or migration changes. Local modular monolith; existing adapter
factories enforce credentials and egress. Tiny synthetic diagnosis is authorized;
suite/lint/typecheck/benchmark/security verification remains deferred by the human.
No new latency or model-quality goal is introduced.

## Constitution Check

Pre- and post-design review aligns with principles I–VI: model/server/domain roles
stay unchanged, no retired path is restored, vendor details remain in adapters,
retry/concurrency/accounting are unchanged, original inputs are never dispatched by
development diagnostics, and implementation does not close release gates.
Continue from `9de3d9d` because it contains the current consolidated implementation;
main is the older architecture. No unresolved design or research unknowns; no
research delegation is needed for this bounded source-supported repair.

## Project Structure

- `backend/src/career_assistant/adapters/providers/schema_dialects.py`: conversion.
- `backend/src/career_assistant/adapters/providers/openai/errors.py`: response
  classification and safe diagnostics.
- Existing OpenAI completion, embedding and `tool_calling.py`: reuse classifier.
- `backend/tests/unit/test_schema_dialects.py` and `test_openai_errors.py`:
  authored regression/privacy tests, not executed.
- Current provider/run docs, PLAN/BACKLOG, development log and engineering journal.

## Delivery Phases

1. Author schema regressions before implementation; preserve explicit nullable
   arrays and defaults, inspect actual CV/advert/letter/judge contracts.
2. Repair array/null conversion; reproduce accepted request with the configured
   OpenAI builder and tiny synthetic data only, without storing responses.
3. Author error-classification/log privacy regressions, then wire a shared OpenAI
   classifier into all three operations. Bodies are decoded only in bounded memory;
   logs contain fixed categories and allowlisted codes/parameters, never messages.
4. Inspect diffs, document debugging evidence and all pending checks, then commit.

## Complexity Tracking

No new abstraction at an application port, storage model, external contract or
material architecture choice. The helper removes repeated vendor error handling.
