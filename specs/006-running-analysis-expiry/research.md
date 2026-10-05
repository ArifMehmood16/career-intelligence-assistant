# Findings

- Decision: enforce existing running expiry in the live worker loop. Source and
  read-only metadata show startup-only recovery; original provider-wait cause is
  unproven. Alternative: change model/HTTP budget, rejected without causal evidence.
- Decision: use existing job row locks and failure publication rather than a new
  queue/watchdog service. Terminal state re-read prevents late overwrite.
- Decision: retain batched judging and show completion guidance. Zero finished
  requirements can mean a whole batch is pending; inventing intermediate progress
  would violate validated-output accounting.
- Decision: reuse cooperative cancellation before retries. Existing post-response
  checks prevent publication but resilience retries also need dispatch checks.
- OpenAI documentation reviewed for the selected gpt-5-mini model; no model or
  reasoning setting changes are needed for this bounded lifecycle repair.
