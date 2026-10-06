# Research: Retirement verification

## Populated upgrade

- Decision: reuse session_factory/migrated_engine and explicit TEST_DATABASE_URL, downgrade one revision to b2d9c8e4f601, seed historical and retained rows, then upgrade_head with restoration in finally.
- Rationale: existing retirement unit tests render constraint SQL; migration repeatability tests cycle an empty schema. Neither proves original or publication preservation. Existing integration fixtures already isolate and reset the dedicated schema.
- Alternatives considered: a new database per case needs extra managed-server permissions; testing only generated SQL would miss cascades and data loss. Personal database migration is excluded.
- Research source: repository inspection plus one read-only agent required by speckit-plan. No external API knowledge or new technology choice needed.

## Shared projections

- Decision: retain ScoreExplanation/ScoreComponent, Requirement/Claim/RequirementMapping and citation value types where consumed. Verify their values originate in SqlV2AnalysisRepository and published_bundle rather than deleting files by historical naming.
- Rationale: scoring.py now contains only immutable view types; application/roles/analysis.py projects persisted current components. Removing these would break grounded generation while providing no retirement benefit.
- Alternatives considered: an API-wide rename is unrelated and would expand scope; rebuilding consumers would duplicate the working publication path.

## Gate scope

- Decision: synthetic SQL/API/tool regression checks and current component suite prove Phase 19.1 flows. Broader browser journey and live model quality/latency remain 19.4.
- Rationale: no paid calls are needed to verify migration and consumer invariants. Existing test adapters run the same chunk/search/judge application pipeline.
- Alternatives considered: the benchmark is a later item; synthetic gallery alone cannot establish persistence/citation integrity.

## Historical live jobs

- Decision: correct the existing retirement upgrade while the v1 marker still exists: fail queued/running retired jobs with a safe retirement code, finish them, clear their old tasks and mark analysing roles failed only when they have no active current job or valid current publication. Preserve current queued/running jobs exactly.
- Rationale: read-only research found that the migration relabels legacy live jobs as v2 without terminalizing them. The worker can silently execute old queued requests or leave running ones blocking concurrency.
- Alternatives considered: a subsequent migration cannot safely recover the overwritten v1 identity on already-migrated installations. Heuristics based on missing task rows could fail legitimate current jobs, so no broad retroactive repair is attempted. Historical applied installations retain existing runtime expiry behavior; this correction protects upgrades crossing the retirement revision.
