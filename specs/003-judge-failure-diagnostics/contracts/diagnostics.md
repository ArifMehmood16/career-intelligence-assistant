# Diagnostic contract

- provider.transport_failed: error_category=timeout or transport_error;
  timeout_phase=connect/read/write/pool/unknown for timeout; timeout_seconds.
- judge.call_failed: provider_id/model_tag, phase=initial/repair, requirement_count,
  error_category=truncated/input_too_large/invalid_output/refused/transient/structured_output.
- judge.verdicts_rejected: phase, requirement_count, accepted_count/rejected_count.
- judge.incomplete: requirement_count, accepted_count/incomplete_count.

No exception message, URL, body, problem string, requirement ID, prompt or response.
Existing retry/exception/public failed-job contracts remain authoritative.
