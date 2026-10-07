# Research: Current plan disposition

Reviewed 2026-10-07 before implementing this slice.

## Provider contracts (19.2)

Decision: verify and reuse the implementation. DocumentChunker already combines
ranges/details/requirements/taxonomy, rejects coverage loss, and bounds repairs and
splits. Judge batches reserve input/output capacity, cache verdicts, batch changed
rechecks and skip unchanged evidence. Native embedding adapters batch inputs;
DocumentIndexer avoids cached probes and serializes shared CV indexing within a
process. Injected execution profiles, separate builders, hosted rate headers and
local/shared gates already exist. Existing focused tests pass; no new provider
implementation is justified. Evidence commands are in quickstart.md.

Alternative rejected: reimplement these unchecked roadmap features. Their status
was stale, rather than their behavior absent. Recorded transport fixtures do not
prove live model quality.

## Runtime contracts (19.3)

Decision: add missing lifecycle acceptance tests. Read-only research agent found
48 existing runtime tests passing. Parallel analysis, repairs, input ordering,
call counting and ETA are covered. Parser timeout/crash termination and app closure
lack direct regressions; generic ContextVar fanout coverage lacks actual combined
cancellation/progress/accounting proof. Production logic is already present.

Reuse ProcessUploadParser, copied contexts, TrackedProgress and ResiliencePolicy.
Reject replacing pools or concurrency abstractions without a demonstrated defect.

## Remaining roadmap (19.4 and Later)

Decision: retain real release work and remove duplicate execution requests.
One complete synthetic Playwright journey can satisfy both duplicated browser
smoke requests; reproducible startup remains separately required. Populated
retirement checks and migration cycles are verified; progress migration
preservation and dependency/security checks still need their own evidence.
Offline benchmark execution remains pending; it cannot establish frozen-label
quality or live-model latency. Ask hybrid retrieval remains relevant; persistent
tool history and durable audit retention remain conditional product decisions.
The test-provider catalogue cleanup remains a small future usability task.
Authentication/OCR/employer screening stay outside this private-tool slice.

PRs 46 and 47 are merged; local main was clean and synchronized at 6340cd0 before
creating this sole task branch. The human-added npm lock remains untouched;
Bun remains the configured package manager. No private database is accessed.
