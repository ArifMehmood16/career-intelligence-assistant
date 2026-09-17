# ADR 002 — PostgreSQL with pgvector

- Status: accepted
- Date: 2026-09-18

## Context

The product stores structured data (documents, spans, requirements, claims,
mappings, scores) and vectors used to propose mapping candidates. A dedicated vector
database would mean two stores to run, back up, migrate and keep consistent.

## Decision

PostgreSQL 16 with the pgvector extension. SQLAlchemy 2 for access, Alembic for
migrations.

## Consequences

- Relational integrity between a span and its embedding, in one transaction.
- One backup and restore story; one deletion path for personal data.
- Vector search scales less far than a dedicated engine. Acceptable for workspace
  scoped corpora of tens of documents.
- Migration to a dedicated store, if ever needed, happens behind the existing
  retrieval port.
