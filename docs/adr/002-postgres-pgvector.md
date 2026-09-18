# ADR 002 — PostgreSQL with pgvector

- Status: accepted
- Date: 2026-09-18

## Context

The product stores personal and structured data: original CV, job-description and
supporting-cover-letter bytes; normalised text and spans; requirements, claims,
mappings and scores; generated drafts; conversations, questions, final answers and
citations; provider provenance; and vectors used to propose mapping candidates. A
dedicated vector database, filesystem upload directory or separate object store would
mean multiple stores to secure, back up, migrate, delete and keep consistent.

## Decision

PostgreSQL 16 with the pgvector extension is the system of record. SQLAlchemy 2 is the
adapter implementation and Alembic owns the schema. Application tables live in the
dedicated Postgres schema `career_assistant`, not `public` (extensions such as
`vector` remain in `public`). Bounded original uploads are
stored in `bytea`; configured admission limits keep them small enough for this
portfolio workload. Fakes are permitted in tests only—there is no SQLite, filesystem
or process-memory production fallback.

The two supported topologies use the same schema and adapters:

- `make run` connects to the developer-managed local PostgreSQL named by
  `DATABASE_URL`, documented as `localhost:5432` by default;
- Docker Compose and deployment connect the API to a PostgreSQL 16 + pgvector
  container on the private Compose network at `db:5432`, backed by a persistent
  volume. Development may publish host port 5433; deployment does not publish the
  database port and requires non-default credentials.

Uploaded cover letters are supporting documents. They may be retrieved and cited in
answers but cannot produce candidate claims or affect mappings and scores. Generated
cover letters are immutable draft records linked to their role-analysis version and
cited CV spans.

## Consequences

- Relational integrity between originals, spans, embeddings, questions, answers,
  citations and generated artefacts, with explicit transaction boundaries.
- One backup and restore story; one deletion path for personal data.
- Questions and only final validated answers are durable. Partial stream tokens and
  raw provider payloads are not stored as answer history.
- Database size grows with original uploads and chat history. Admission limits,
  retention, hard delete, backup rotation and a measured backup/restore procedure are
  required controls.
- Vector search scales less far than a dedicated engine. Acceptable for workspace
  scoped corpora of tens of documents.
- A later move to object storage or a dedicated vector store requires a new ADR and
  must preserve atomic deletion and workspace scoping.
