# Verification guide

1. From the root run `make lint` and `make test`; preserve existing coverage gates.
2. Use an isolated disposable PostgreSQL/pgvector database with explicit distinct
   DATABASE_URL and TEST_DATABASE_URL; run `make test-integration`. Never source
   the ignored personal app configuration or target its data.
3. Push the updated existing PR branch, inspect the run for its exact head, and
   observe hermetic plus PostgreSQL 16 and Supabase 17 job outcomes.
4. Report only observed results. Quality/latency/browser release gates remain open.

Managed-server regression: tests/integration/test_engine_defaults.py deliberately
starts with extra_float_digits=0 and checks exact read-back; the application
connection overrides it. The RLS probe grants SET membership transactionally and
asserts its effective role, then checks zero visible rows. No tolerance or bypass
was added to obtain green checks.
