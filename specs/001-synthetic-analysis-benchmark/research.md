# Inspected design decisions

- Decision: reuse `application/analysis/v2.py` directly. Rationale: it executes the
  running reader/search/judge/domain-score workflow. Rejected: reintroducing the v1
  evaluator or benchmarking a custom shortcut.
- Decision: use the existing hermetic `InMemoryIndexStore` and `IndexBackedSearch`
  only as explicit measurement fixtures. Rationale: no personal database, migrations
  or new storage adapter is needed. Limitation: live provider measurements exclude
  PostgreSQL and browser latency; they cannot establish production retrieval quality.
- Decision: count physical API attempts at `HttpTransport.request`, with separate
  completion, embedding and metadata buckets. Rationale: a logical structured call
  can trigger schema repairs and transport retries, and model digest lookups occur
  outside completion accounting. Retain progress counters separately for task context.
- Decision: report cache reads/hits at index and verdict-cache boundaries. Rationale:
  warm retrieval still makes query embeddings; zero document reads is not zero work.
- Decision: only named manifest cases and a fixed analysis date; record SHA-256
  fingerprints of consumed bytes, models config and rubric. Rationale: comparisons
  require identical inputs without copying evidence into operational output.
- Decision: apply `op.f()` to full constraint names in the retirement revision,
  including downgrade embedding checks. Rationale: `models.Base` uses
  `ck_%(table_name)s_%(constraint_name)s`; the reported SQL double-prefixed names.
- Validation state: inspection only. Installed source was read; no tests, lint,
  benchmark or migrations executed. No external research or model agents needed.
