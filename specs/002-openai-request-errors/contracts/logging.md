# Operator log contract

Event `provider.request_failed` records provider_id=openai, model_tag, operation
(completion, embedding or tool_calling), http_status, error_category,
provider_error_code and parameter. Known vendor code/parameter literals may be
retained; unknown values use `unknown`. Correlation/workspace context remains the
existing logging context. No error message or HTTP payload is emitted.

Current job polling still returns HTTP 200 with state=failed and the safe
mapping_failed error when analysis fails. This diagnostic addition does not change
that public error envelope or retry classification.
