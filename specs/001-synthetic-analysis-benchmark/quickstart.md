# Pending validation guide

Execution remains deferred by the human. Commands below are future checks, not
observed results. Existing backend dependencies from `make setup` are required.

```bash
cd backend
.venv/bin/pytest tests/unit/test_analysis_benchmark.py tests/unit/test_retirement_migration.py --no-cov
cd ..
make benchmark BENCHMARK_ARGS='--case clean_match --repetitions 3'
mkdir -p tmp
make benchmark BENCHMARK_ARGS='--case clean_match --output tmp/benchmark.json'
```

Inspect cold/warm ordering, fingerprints, fixture labels, zero physical requests,
cache reuse and non-null elapsed time only for work executed. Compare the successful
pair's score and requirement count. Warm retrieval may still embed queries.

A separately requested local experiment:

```bash
make benchmark BENCHMARK_ARGS='--live --provider ollama --embedding-provider ollama --case clean_match'
```

Hosted measurements require existing enabled keys as well as `--live`. Never use
personal documents; there is no custom document path option. Live model timing uses
fixture retrieval; SQL/browser latency and quality labels remain separate 19.4 work.
Retry the repaired personal migration only at the human's discretion with
`make db-migrate`; disposable PostgreSQL preservation/deletion checks remain pending.
