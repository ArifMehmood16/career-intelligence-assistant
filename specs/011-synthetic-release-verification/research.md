# Research decisions (2026-10-07)

Read-only agents inspected startup/browser and additive-progress migration.
Decision: use real SQL worker and proxy with hermetic adapters; reject in-memory
API fixtures for browser acceptance. No browser runner exists, so Playwright is a
test-only workspace dependency. Official Playwright webServer/config docs confirm
managed multiple servers, explicit env, refusal to reuse services and graceful exit.

Decision: preserve source/resource layout in the image and migrate on startup;
reject only adding a migration CMD to the current broken wheel image, because its
import-time rubric/model paths would still fail. Root-context explicit COPY avoids
secret inclusion. Host startup remains available independently.

Decision: test c1f7a2d94e08 -> b2d9c8e4f601 with populated raw task rows and restore
head in finally. Current ORM assumes new fields, so it cannot read the old revision.
No destructive operation reaches the application database.

Decision: fix existing text-file description control; it currently posts filename.
Binary description upload needs its own supported server flow, not fake JSON text.

Observed benchmark: 36 successful offline observations (six pairs, three cold/warm
repetitions), source 9c2f27e clean, zero physical requests. Save with fingerprints.
Observed initial scans: frontend 1 critical/5 high advisory findings; Python reports
cryptography findings whose fixes require up to 50.0.0, beyond current <47 range.
Bandit has 20 findings (2 medium, 18 low), not a clean pass; triage is required.
Docker engine is now running; local qwen2.5:7b/nomic are installed. No paid calls.
