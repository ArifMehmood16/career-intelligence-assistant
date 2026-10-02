# Validation and retry guide

All pytest/lint/typecheck/benchmark checks remain deferred. When authorized, run
focused unit schema/error tests and normal release checks from AGENTS.md.

The human can restart the API or allow the development reloader to load the change,
then start a new analysis. Existing failed jobs do not resume automatically. A
successful schema submission establishes only request acceptance, not a complete
analysis or a validated model answer.

If the new job fails, inspect the preceding provider.request_failed event for
operation, model, status and fixed error category. Do not enable raw HTTP/body
logging or paste credentials/documents for diagnosis. The existing egress gate and
original schema/evidence validators must stay enabled.
