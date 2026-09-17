# ADR 003 — Pluggable model providers with a local default and an enforced egress gate

- Status: accepted
- Date: 2026-09-18

## Context

A CV is personal data, and a set of job applications reveals intent the candidate
may not want disclosed. Sending that to a hosted API places it under a third party's
retention terms. At the same time, extraction quality is exactly where a frontier
model earns its cost, and some users will happily accept those terms for it.

Two positions are both defensible and both wrong as absolutes. "Local only" makes the
product unusable for teams who want frontier quality and have already accepted a
vendor's terms. "Hosted only" makes it unusable for everyone who cannot send this
content anywhere — which, for this corpus, is a large share of the realistic users.

The choice is also not static. It changes per deployment, per customer, and sometimes
per workspace inside one customer. Anything that bakes it in at build time is wrong by
the second deployment.

## Decision

The completion and embedding ports each have several adapters: a hermetic default that
needs no network or keys, a local Ollama adapter, an OpenAI adapter, and an Anthropic
adapter. The active provider is a runtime setting, not a rebuild.

Hosted adapters are reachable only through an enforced egress gate. A hosted adapter is
constructible only when `ALLOW_HOSTED_PROVIDERS` is true **and** that provider's key is
present. The gate is one chokepoint in the application layer, and a test asserts no
adapter can reach the network around it.

The two ports are independent. Local embeddings with a hosted completer is a supported
and sensible configuration, and Anthropic serves no embedding model, so that pairing is
required rather than exotic.

Every adapter passes the same contract test suite. An adapter that cannot satisfy the
contract is fixed or removed — never special-cased in the application.

## Consequences

- The abstraction is the deliverable. Swapping vendors is a setting, and the evidence
  it works is that the same contract suite passes on all of them.
- Default runs stay hermetic: a reviewer clones, runs and tests with no key and no
  model download.
- Quality, latency and cost become measurable rather than assumed. The same evaluation
  dataset runs on each provider and the comparison is published, including the cases
  where the local model holds up.
- Content leaving the machine is a deliberate, visible act: configuration to enable it,
  a workspace setting to select it, a notice in the UI, and the provider recorded
  against every answer.
- Providers differ in structured-output support, context window and rate limits. The
  port carries a capability descriptor and the application degrades deterministically.
  It never branches on a provider's name.
- Supporting several vendors costs more than supporting one: more adapters, more
  contract tests, more failure modes. Accepted, because it is the point.
