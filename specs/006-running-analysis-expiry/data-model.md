# Existing data model

No migrations or new entities. AnalysisJob keeps queued → running → succeeded or
failed. A running row older than its configured timeout becomes failed with
`stale_running`, finished_at and a safe message. Row locks serialize failure with
publication. A terminal/deleted row must never be revived by a late failure.
Existing AnalysisTask progress is settled by the API for failed jobs. Role failure
retains the existing prior-publication restoration policy; an initial incomplete
analysis has no published score or verdicts.
