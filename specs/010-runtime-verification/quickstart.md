# Runtime verification guide

Use the existing backend virtual environment and Bun installation. No provider key,
application env file, personal upload or database is needed.

From backend, provider acceptance:

```bash
.venv/bin/pytest tests/unit/test_document_chunker.py tests/unit/test_chunk_plan.py tests/unit/test_judge_prompt.py tests/unit/test_requirement_judge.py tests/unit/test_corrective_retrieval.py tests/unit/test_document_indexer.py tests/unit/test_embedding_input_types.py tests/unit/test_call_gate.py tests/unit/test_local_call_gate.py tests/unit/test_hosted_structured_requests.py tests/unit/test_openai_errors.py tests/contract/test_capability_profile_contract.py tests/contract/test_embedding_contract.py tests/unit/test_model_catalogue.py tests/unit/test_provider_catalogue_wiring.py --no-cov
```

Runtime acceptance (after test implementation):

```bash
.venv/bin/pytest tests/unit/test_process_parser.py tests/unit/test_fanout.py tests/unit/test_parallel_analysis.py tests/unit/test_provider_progress.py tests/unit/test_tracked_progress.py tests/unit/test_job_progress.py tests/api/test_parser_lifespan.py --no-cov
```

Expected: synthetic timeout/crash returns the existing unreadable error, child
workers terminate, fresh parsing succeeds and app shutdown releases workers.
Parallel retries have exact task counts; cancelled work never dispatches.

From root, run `make lint` and `make test`. SQL integration is required if a
persistence defect demands a change; otherwise unchanged SQL coverage is observed
in final-head CI. Browser journeys, benchmarks and security scans are separate
19.4 tasks and are not proven by these commands.
