# Model providers

Completion and embeddings each sit behind a port with four adapters. Which one is
active is a runtime setting a user can change, not a rebuild.

| Provider | Completion | Embeddings | Content leaves the machine | Needs |
|---|---|---|---|---|
| `hermetic` (test fixture) | Rule-based extraction | Lexical hashing | No | Nothing; selected by `make test` |
| `ollama` (product default) | `qwen2.5:7b` | `nomic-embed-text` | No | Ollama running with both models pulled |
| `openai` | Chat API | Embeddings API | **Yes** | `OPENAI_API_KEY` and the egress gate open |
| `anthropic` | Messages API | — | **Yes** | `ANTHROPIC_API_KEY` and the egress gate open |

Model tags are configuration (`config/app.env`), never hard-coded. The completion model
is part of the assessment contract rather than a preference: on the labelled pilot,
`qwen2.5:7b` disagreed with the labels on 3 of 24 requirements and `llama3.2` on 12,
including crediting an injection attempt as a match
([docs/evaluation.md](evaluation.md)).

The two ports are independent on purpose. Anthropic serves no embedding model, so
selecting it for completion leaves embeddings wherever they already were — and local
embeddings with a hosted completer is a sensible configuration in its own right.

## The egress gate

Hosted providers are unreachable unless two things are true: `ALLOW_HOSTED_PROVIDERS`
is on in server configuration, and that provider's key is present. A single enforced
chokepoint makes the decision at construction **and** on every complete or embed
call. Closing the gate after an adapter was built still refuses and makes no network
attempt, and a test asserts that.

Within what the server permits, the active provider is a workspace setting changed in
the UI. Choosing a hosted one shows a notice saying CV, job-description, supporting
cover-letter and question text may be sent to that provider — and the server rejects
the change without an explicit acknowledgement, so the confirmation is not merely a
UI convention. Every answer and every draft records which provider and model produced
it.

**Keys live in server configuration only.** No route accepts, returns or displays a
key in any shape, including masked. Enabling a hosted provider is an act performed on
the server by someone who has accepted what it means.

## Why not just pick one

Committing to local makes the product unusable for a team that wants frontier quality
and has already accepted a vendor's terms. Committing to hosted makes it unusable for
everyone who cannot send application-document text anywhere. Both are real customers,
and which one is in front of you is not knowable at build time. So the switch is the
feature, and the abstraction that makes it safe is the engineering.

Providers differ in structured-output support, context window and rate limits, so the
port carries a capability descriptor and the application degrades deterministically.
The same labelled dataset is meant to run on every provider, with quality, latency and
cost side by side; that comparison is PLAN 14.5 and has not been run yet.
