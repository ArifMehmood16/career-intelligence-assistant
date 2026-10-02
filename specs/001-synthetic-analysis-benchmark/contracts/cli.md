# CLI and report contract

`python -m career_assistant.ops.benchmark [--case NAME ...] [--repetitions N]
[--as-of YYYY-MM-DD] [--output PATH] [--live --provider PROVIDER
--embedding-provider PROVIDER [--completion-model TAG] [--embedding-model TAG]]`

Defaults: all manifest pairings, one repetition, analysis date 2026-09-01,
hermetic completion/embeddings, JSON to stdout. Offline execution ignores provider
settings and cannot make transport requests. Real provider selection requires
`--live`; hosted requests additionally require the existing enabled/keyed gate.
Live completion: ollama/openai/anthropic. Live embeddings: ollama/openai.
Explicit model tags override the existing configured defaults. Fallback is disabled.

Report fields follow [data-model.md](../data-model.md). Each case/repetition emits
cold then warm. Physical completion/embedding requests, metadata requests, logical
operations and progress attempts are separate. No score is emitted after failure.
Output files are created exclusively; existing files are never overwritten.
Exit 0 means all observations completed; exit 1 means observed analysis failure;
exit 2 means invalid arguments or an unwritable report destination. Provider
construction failures (including a closed egress gate) are recorded failures with exit 1.
No raw exception messages reach the output. Public HTTP contracts are unchanged.
