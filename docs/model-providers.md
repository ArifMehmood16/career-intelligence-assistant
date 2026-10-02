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

## Model limits and structured output

Each model tag's context window, output limit and capabilities — tool calling, prompt
caching, and whether it accepts a temperature or a seed — come from
[config/models.toml](../config/models.toml). A tag the file does not name uses its
provider's conservative defaults. Add a row when you configure a new model tag.

Where the model supports it (`native_structured_output` in the catalogue), the
provider's API enforces the JSON schema. Otherwise the adapter includes the schema in the prompt.

| Provider | Native structured output | Otherwise | Truncation |
|---|---|---|---|
| Ollama | `/api/chat` with the schema as `format`; `num_ctx` is always sent from the catalogue, so the prompt window is the one the descriptor reports | — (every model) | `done_reason: length` |
| OpenAI | `json_schema` with `strict: true`; the schema is adapted to strict mode, and the nulls strict mode forces into optional fields are removed from the reply | `json_schema` without `strict` | `finish_reason: length` |
| Anthropic | `output_config.format`, with the schema adapted to the supported subset of JSON Schema | The schema in the prompt. The configured default, `claude-sonnet-4-0`, is on this path: Anthropic lists structured outputs from Sonnet 4.5 | `stop_reason: max_tokens`, reported as `length` |
| Hermetic | Scripted, schema-shaped fixtures | — | — |

OpenAI strict mode requires every property. Non-nullable lists with empty-list
defaults stay arrays: the model returns `[]` rather than a null sentinel. Other
optional fields may become nullable; fields already allowing null keep one null
alternative. This repairs the reproduced advert-reading format rejection while
the original Pydantic contract and evidence checks remain authoritative.

Constraints an API cannot enforce, such as a numeric range, move into the field's
description. Temperature and seed are sent only when the catalogue says the model
accepts them.

Embedding requests say whether they embed a query or a document, and the catalogue's
prefixes for that model are applied — `search_query:` and `search_document:` for
`nomic-embed-text`. A request with no input type is embedded exactly as before.

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

## Rate limits

Rejected OpenAI completion, embedding and tool requests emit
`provider.request_failed` with provider/model, operation, HTTP status, a fixed error
category and allowlisted vendor code/parameter. Unknown values become `unknown`;
raw vendor messages, response bodies, prompts and credentials are never logged.
The existing HTTP retry classification remains unchanged. A job can be failed
even when polling its status returns HTTP 200.

Hosted completion and embedding share one process-wide gate. It is selected from
`leaves_machine` on the capability descriptor, so Ollama and the hermetic fixture
never enter it. Their model profiles supply tunable local concurrency; a shared
local slot gate enforces that cap across concurrent roles and tool calls. `HOSTED_MAX_IN_FLIGHT` (default 4) caps
how many hosted calls are in flight. That is a burst cap. The account's real
allowance is read from the last response, and no tier is hard-coded.

| | Remaining | Reset | 429 wait |
|---|---|---|---|
| OpenAI | `x-ratelimit-remaining-requests`, `x-ratelimit-remaining-tokens` | `x-ratelimit-reset-requests`, `x-ratelimit-reset-tokens`, as a duration such as `1s` or `6m0s` | `retry-after` or `retry-after-ms` |
| Anthropic | `anthropic-ratelimit-requests-remaining`, `anthropic-ratelimit-input-tokens-remaining`, `anthropic-ratelimit-output-tokens-remaining` | the matching `*-reset` headers, as an RFC3339 time | `retry-after`, in seconds |

The token bucket is the tighter of whichever token headers the response carried.
For Anthropic that is the smaller of the input and output buckets. Before a call
starts, the gate reserves an estimate (`len(prompt) / 4` plus the output cap for a
completion; the summed text length for an embedding). If the stored remaining
requests or tokens cannot cover it, the call waits until that header's reset, and
never longer than 60 seconds. A 429 waits for the vendor's `Retry-After`, with the
same cap. A 429 that carries no `Retry-After` is not retried: a monthly spend cap
is that case, and another attempt will not succeed.

Cache reads do not count toward Anthropic's input-token limit for current Sonnet
models; cache writes do. The first wave of parallel judge batches misses the cache
and pays full input tokens. The gate, not a serial warm-up, is what keeps that wave
inside the allowance.

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

## Execution profiles and call reduction

Provider modules independently construct completion, embeddings and tool callers.
`completion_concurrency`/`embedding_concurrency` bound execution; defaults are 1 for
Ollama and 4 for hosted providers. `document_output_tokens`/`judge_output_tokens`
are operational caps, with 0 allowing the model's maximum. `tokens_per_verdict`
estimates output when packing; `max_document_split_depth` bounds fallback splits.
The input/output ceilings both constrain requests. Update the row for each real
model tag instead of inheriting an unknown tag's conservative defaults.

A fitting document returns chunks, details, atomic requirements and technology
relations in one call. Judging packs all fitting requirements together. Corrective
judgments batch changed candidates only. CV index locks and known embedding model
identity eliminate repeated read/probe calls. Ollama embeds arrays through
[/api/embed](https://docs.ollama.com/api/embed), with truncation disabled; OpenAI
also accepts input arrays. Counts include physical attempts and retries, while
remaining calls are explicitly estimates.

The configured `gpt-5-mini` has an explicit catalogue row: published 400,000 context
and 128,000 maximum output tokens, with 32,768 operational output caps for document
reading/judging. Reasoning consumes output tokens. The caps are tunable, and no
live quality/latency measurement is claimed.
[Official model documentation](https://developers.openai.com/api/docs/models/gpt-5-mini),
[reasoning-token guidance](https://developers.openai.com/api/docs/guides/reasoning).
