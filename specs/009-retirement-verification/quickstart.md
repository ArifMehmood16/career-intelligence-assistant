# Validation guide

Use installed backend/.venv and frontend dependencies. Use a disposable PostgreSQL/pgvector instance with distinct application and test database URLs; never source personal config for these commands.

1. Run `cd backend && .venv/bin/pytest -m integration tests/integration/test_retirement_preservation.py tests/integration/test_publication_consumers.py --no-cov` with explicit DATABASE_URL and TEST_DATABASE_URL. The populated migration test restores head in finally.
2. Run focused current-worker, architecture, v2-schema and existing hard-delete tests. Expect no retired execution, same publication values, preserved originals/current rows and workspace-scoped deletion.
3. Run `make lint`, `make test` and `make test-integration` with the same explicit disposable URLs for the SQL command.
4. Inspect `git diff main...HEAD`, run available changed-file security tooling, and record observed results in the engineering journal. Run all three CI jobs on the final pushed PR head.

All analysis and generation use synthetic fixtures and hermetic adapters. This does not validate live provider quality/latency or the separate full-browser release gate.
