# Research: PR #43 CI repair

- Decision: align tests to current modules instead of restoring removed adapters.
  Rationale: both database jobs stop on the same five collection errors. The
  retired embedding adapter and rubric version are superseded; job guards moved.
  Alternative rejected: production compatibility shims for unused v1 behavior.
- Decision: retain existing quality thresholds and execute checks after initial
  blockers are repaired. Rationale: user explicitly resumes CI verification.
  Alternative rejected: skips, suppressions, reduced coverage or green claims
  based only on collection/formatting.
- Decision: run checks on synchronized and reopened PR heads as well as opened.
  Rationale: the current opened-only workflow leaves updates unchecked.
- Decision: isolate local database data and use CI for both supported images.
  Rationale: personal app is online and tests downgrade/truncate their database.
  No paid provider calls or personal inputs are needed.

## Managed PostgreSQL follow-up

The first repair run passed PostgreSQL 16 and lint/typechecks, but exposed four
Supabase float round-trip failures and restricted SET ROLE. Reduced precision was
reproduced on the disposable PostgreSQL 17 database with extra_float_digits=0.
Application connections now request shortest-precise float output; exact score and
trace assertions stay intact. The RLS probe explicitly grants SET membership and
asserts the effective identity before checking that no rows are visible.

Primary references: [PostgreSQL float output defaults](https://www.postgresql.org/docs/16/runtime-config-client.html)
and [PostgreSQL 17 role creation](https://www.postgresql.org/docs/17/role-attributes.html).
These are connection/test portability repairs; no scoring arithmetic, policy or
provider behavior changes. The new regression supplies reduced startup precision
explicitly, independent of the host defaults.

The hermetic failures in that run were documentation contracts absent from the
first push. Current feature/threat-model docs are now committed with their actual
boundaries, and full local checks include them.
