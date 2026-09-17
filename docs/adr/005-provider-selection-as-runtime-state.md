# ADR 005 — Provider selection is runtime state, not deployment configuration

- Status: accepted
- Date: 2026-09-18

## Context

The obvious way to make providers switchable is an environment variable. It is also the
wrong granularity. The person who decides whether a CV may be sent to a third
party is the person using the product, not whoever last edited a deployment manifest.
Restarting the service to answer one question with a stronger model is not a workflow.

## Decision

Server configuration decides what is *permitted*: which keys exist, and whether hosted
egress is allowed at all. A workspace setting decides what is *used*, within that
permission, and it can be changed in the UI.

The API exposes the available providers and, for each unavailable one, the reason — no
key, egress disabled, service unreachable. It never returns a key, in any shape,
including masked.

Every answer and every stored artefact records the provider and model tag that produced
it, and whether content left the machine.

## Consequences

- Choosing a hosted provider is an informed act by the person whose a CV it
  is, taken in front of a notice that says where the text is going.
- Stored artefacts are attributable. "Which of these were produced by the local model?"
  is a query, not an archaeology exercise.
- Comparing providers is a click, which is what makes the evaluation table honest — the
  numbers come from a path users actually take.
- Mixed-provider histories are possible inside one workspace. That is accepted and made
  visible rather than prevented, because forcing a re-extraction on every switch would
  be worse.
- Permission cannot be escalated from the UI. A workspace can only select from what the
  server already allows, so an exposed frontend cannot turn on egress.
