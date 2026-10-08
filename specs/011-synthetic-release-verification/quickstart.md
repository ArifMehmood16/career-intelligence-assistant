# Validation guide

Offline benchmark: `make benchmark BENCHMARK_ARGS='--repetitions 3 --output tmp/benchmark.json'`.
Use an unused destination. No credentials, DB or network are needed.

Browser: install `e2e` with Bun and its Chromium browser; provide only a dedicated
`E2E_DATABASE_URL` ending in `_e2e`, then `make test-e2e`. The test setup migrates it
and starts isolated API/web servers with hermetic providers and hosted egress closed.
Never point it at the personal application database or existing browser session.

SQL: explicit distinct DATABASE_URL/TEST_DATABASE_URL, focused populated progress
migration test, then `make test-integration`. Test fixtures restore migration head.

Checkpoint: `make lint`, `make test`, browser journey, startup and release scans.
Record actual commands/results and open blockers in existing engineering/evaluation docs.
Local model runs use shipped synthetic fixtures and explicit local provider tags.
Hosted requests are outside this instruction unless separately authorized.
