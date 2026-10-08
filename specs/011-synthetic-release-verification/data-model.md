# Existing data and evidence

No production entity/wire schema change. Additive migration tests exercise existing
job_tasks identities/state/units/timestamps and new model/embedding counters.
Test-only browser workspaces live in a dedicated _e2e database and use only shipped
synthetic documents. Reports store fingerprints/counts/durations/model attribution,
never document text, prompts, responses, keys or endpoints. Frozen quality labels
are explicitly current-architecture synthetic expectations with development scope.
