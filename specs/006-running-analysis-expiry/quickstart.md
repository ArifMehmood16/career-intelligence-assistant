# Synthetic validation

Use the repository development Python/Bun dependencies. Run the focused worker,
resilience and AnalysisProgress tests before full `make lint` and `make test`.
Configure DATABASE_URL and TEST_DATABASE_URL to different disposable databases;
never use the personal application database. Run `make test-integration`.
The expiry regression blocks a synthetic provider, advances the injected clock,
observes failed/unscored HTTP state before release, then verifies no late publish.
Do not run a real hosted analysis to validate this change.
