# Productionisation

The modular monolith moves to a hyperscaler without a redesign. What would change:

| Here | On AWS, GCP, Azure or Cloudflare |
|---|---|
| Make or Compose on one machine | API, worker and Nitro web server as separate containers on ECS Fargate, Cloud Run or Azure Container Apps |
| In-process analysis worker | A worker service fed by a managed queue (SQS, Pub/Sub or Service Bus), with the PostgreSQL job table still the source of truth |
| Local PostgreSQL + pgvector, originals in `bytea` | Managed PostgreSQL with pgvector (RDS or Aurora, Cloud SQL, Azure Database for PostgreSQL), private networking, encryption at rest and point-in-time recovery; originals move to object storage with KMS keys if volumes grow |
| Local Ollama | In-network model serving on GPU (vLLM or Ollama), or a hosted API under a data-processing agreement; the egress gate and per-answer provenance stay |
| `config/app.env` | A secret manager and workload identity |
| stderr, rotating file, in-memory audit | OpenTelemetry, central logs under the same field contract, audit tables in PostgreSQL, alerts on job failure rate and provider errors |
| Workspace cookie | OIDC sign-in and per-user authorisation — required before any shared deployment |
| Application limits | A gateway or WAF in front (Cloudflare or the cloud's own), rate limits and quotas |
| Manual deletion | A retention job, backup rotation and a tested restore |

Also needed before anyone else uses it: a privacy review, disaster recovery, per-provider
cost monitoring (the accounting table already records tokens), and re-running the
evaluation on every model upgrade.
