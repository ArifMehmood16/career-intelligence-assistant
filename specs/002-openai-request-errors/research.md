# Research and diagnostic evidence

## Decision: retain non-nullable arrays in strict mode

The user's new failed job reports `read_advert` failed after one completion attempt;
CV reading reused its cache. Read-only workspace selection confirms `gpt-5-mini`
and `text-embedding-3-small`. Tiny synthetic CV and embedding requests returned 200.
The actual advert contract reproduced 400 with `response_format` identified. The
safe classifier showed a generic invalid-schema error, not a specific field.

In a temporary diagnostic transport, deduplicating nullable alternatives alone
still returned 400; removing the numeric optional field alone still returned 400;
changing only the outer requirements array still returned 400. Retaining all
original non-nullable arrays as arrays, together with null deduplication, returned
200. Apply that conversion; original defaults allow empty arrays, so all properties
can be required without null sentinels for collections. Do not remove requirements
or weaken the original contract, switch providers, or change timeouts.

## Decision: keep vendor response details in one adapter helper

Existing `classify_http_status` determines retries and typed exceptions. Call it
unchanged after recording fixed categories plus allowlisted error code/parameter.
Unknown values become `unknown`; never sanitize an arbitrary message into a log.
Malformed/oversized bodies cannot prevent status classification. No API/job wire
change or exception hierarchy change is necessary.

Official guidance consulted and fetched:
[Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
and [Error codes](https://developers.openai.com/api/docs/guides/error-codes).
OpenAI requires closed objects and all properties required; optionality may use
null. This repair concerns provider conversion, not a claim that all nullable
arrays are universally unsupported.

## Post-repair observation

With temporary transport schema mutations removed, the repaired application's
OpenAI completion builder submitted the actual JobChunkResponse contract and a
tiny synthetic Python requirement with a 64-token cap. OpenAI returned HTTP 200.
No response content was printed or saved. This establishes request acceptance,
not a complete response, a personal-document analysis or a release gate.
