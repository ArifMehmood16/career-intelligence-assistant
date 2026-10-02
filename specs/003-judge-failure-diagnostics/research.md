# Research

Read-only job progress: cached CV; one advert call; one embedding call; 18 searched
requirements; three physical judge attempts; no rechecks; scoring failed.
Successful-call accounting after 16:04 UTC contains only advert and embedding
entries. Embedding finished 16:06:47 UTC; failure was 16:09:49 UTC. Existing timeout
is 60 seconds with two retries. This suggests, but does not confirm, read timeouts.
HttpxTransport translates timeouts without logging; RequirementJudge then catches
exhausted transient failures and returns no verdicts. Judge progress counts handled
requirements, not accepted verdicts. No public contract change is needed.

The OpenAI reasoning guide explains reasoning tokens and latency tradeoffs; it
cannot identify this individual failure. Preserve gpt-5-mini and current effort.
[Official reasoning guide](https://developers.openai.com/api/docs/guides/reasoning).

Choose a reversible local 180-second limit and safe failure diagnostics. Reject
changing model/effort, inventing missing judgments, weakening evidence checks or
rerunning personal documents. Future synthetic end-to-end verification is deferred.
