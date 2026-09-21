# ADR 001 — Modular monolith with ports and adapters

- Status: accepted
- Date: 2026-09-18

## Context

The system has a small number of clearly separable concerns: document intake,
extraction, mapping and scoring, question answering, and a web UI. Splitting them
into services would add deployment, network and observability overhead without
removing any coupling that matters at this size.

## Decision

Build one deployable backend, internally divided into `domain`, `application` and
`adapters`. Domain and application code import no web framework, no ORM and no
provider SDK. External systems are reached through narrow ports.

## Consequences

- Boundaries are enforced by an architecture guard test, not by convention.
- Any part can be extracted into a service later because the port already exists.
- A single database transaction spans a whole use case, which keeps ingestion simple.
- Horizontal scaling is process-level. Accepted at this size.
- Production persistence is PostgreSQL via `build_sql_stores`. Default tests use
  in-memory fakes through `create_app()`. The live map is
  `docs/production-wiring.md`.
