# Data model: existing entities only

- Workspace scopes every original and derived row. Removing it cascades documents, analysis, chat and audit data.
- Document retains original bytes, normalized text and spans. Retirement must not modify these.
- Role points at its current analysis_version. A ready role without a non-invalidated current score becomes failed at retirement.
- Score explanation carries pipeline_version and analysis_id. Untagged/v1 payloads are erased; v2 payloads are preserved even when invalidated, while readers exclude invalidated rows.
- Generated draft belongs to role + analysis_version and owns draft citations. Retired-score draft removal cascades citations; unrelated current drafts remain.
- Current chunks, embeddings, requirement items, graph nodes/edges, verdicts, evidence and traces retain identities and payloads.
- Analysis job remains operational history. Retired task rows are removed; the pipeline field admits only v2 after upgrade. Inspect active historical jobs explicitly.

No schema or domain entity is introduced by verification.
