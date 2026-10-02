# Verification (deferred)

Restart the local API to load ignored configuration. Effective timeout is 180 seconds
with two retries. A retry may wait up to about nine minutes for three timed-out calls.

Once authorized, run focused test_httpx_transport.py and test_requirement_judge.py
with --no-cov, lint/typecheck, normal tests and a synthetic complete analysis. Inspect
transport/judge logs for categories/counts and absence of private strings. Do not
rerun personal documents as a development check.
