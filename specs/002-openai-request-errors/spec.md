# Feature Specification: OpenAI analysis request repair

**Feature Branch**: `fix/phase-19-openai-request-errors`
**Created**: 2026-10-02
**Status**: Implemented for review; regression verification deferred
**Input**: Debug the reported OpenAI analysis failure after billing was restored.
**Root scope**: [PLAN 19.2](../../PLAN.md#192--reduce-modelapi-calls-and-respect-each-provider), with verification under [19.4](../../PLAN.md#194--prove-the-current-product).

## User Scenarios & Testing

### User Story 1 — Read the advert with OpenAI (Priority: P1)

A candidate using OpenAI must be able to submit the existing advert-reading
contract without an avoidable request rejection.

**Why this priority**: The observed failed job stops while reading its advert.
**Independent Test**: Inspect the real document contracts after provider conversion;
when explicitly authorized, submit only a synthetic advert through the existing gate.

**Acceptance Scenarios**:

1. Given optional collections whose omitted value is an empty collection, when a
   strict response format requires those fields, then the provider can return empty
   collections without a synthetic null alternative being added to their types.
2. Given fields that explicitly allow null, when the schema is adapted, then that
   option remains and is not duplicated.
3. Given an adapted reply, when the server reads it, then the original contract and
   evidence checks remain authoritative; an incomplete analysis produces no score.

### User Story 2 — Understand a provider rejection (Priority: P2)

An operator must be able to identify the rejected operation and error category
without accessing document content or credentials.

**Why this priority**: The current worker log records only an exception class.
**Independent Test**: Supply recorded rejected responses and hostile error payloads;
inspect captured logs for fixed categories, operation, model and HTTP status.

**Acceptance Scenarios**:

1. Given an OpenAI error response, when completion, embedding or tool calling fails,
   then logs identify provider, model, operation, HTTP status and a fixed category.
2. Given arbitrary text in error fields, when it is classified, then no message,
   payload, prompt, endpoint or credential appears in logs. Unknown codes/parameters
   become `unknown`, and malformed or oversized bodies remain safe.
3. Given a transient or permanent rejection, when it is classified, then the current
   bounded retry policy and typed exceptions continue to apply.

### Edge Cases

- Explicitly nullable arrays, optional non-collection fields, references, and nested
  real CV/advert/judge contracts; input schemas must not be mutated.
- Invalid JSON, non-object error payloads, unknown vendor codes/parameters, and error
  messages containing synthetic secrets or document fragments.
- Billing remains an external prerequisite; a successful schema submission does not
  establish a complete model answer or an end-to-end analysis.

## Requirements

- **FR-001**: Provider conversion MUST preserve empty-collection defaults without
  introducing unnecessary null alternatives into optional non-nullable collections.
- **FR-002**: Existing explicit null choices and all server validation MUST remain;
  conversion MUST use a copy and avoid adding a duplicate null branch.
- **FR-003**: Each rejected OpenAI operation MUST emit content-free diagnostics with
  provider/model/operation, status and a fixed error category.
- **FR-004**: Only allowlisted vendor codes and parameter names MAY be retained;
  arbitrary error text and bodies MUST NOT be logged or persisted.
- **FR-005**: Egress, retries, scoring, public job errors and database state MUST
  retain their existing behavior; diagnostic reproduction MUST use synthetic inputs.

### Key Entities

- Adapted response contract: provider-compatible shape, validated by the original.
- Failure diagnostic: identifiers, status, fixed category and allowlisted codes only.

## Success Criteria

- **SC-001**: Synthetic advert schema submission no longer has the reproduced format
  rejection; real contract regression checks cover the conversion.
- **SC-002**: Each rejected operation is distinguishable in captured logs, with zero
  raw error text, request content or credentials retained.
- **SC-003**: Focused regression and normal release checks remain explicitly pending
  until the human lifts the test/lint deferral.

## Assumptions

This is a bounded repair of the current implementation. Use the current consolidated
branch as the dependency base rather than obsolete main. Tiny live synthetic
requests are debugging evidence under the user's request; they are not suite,
benchmark, quality or release verification. Never rerun the user's documents.
