# Data model

No new production entity or wire format is planned. Reuse validated chunks,
verdicts, job guards and published results. Synthetic fixtures must obey current
schema constraints. CI run identity includes run id, reviewed head and each job's
observed state/conclusion. Failure reporting never substitutes a prior head.
