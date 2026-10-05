# Existing API and UI contract

GET /api/jobs/:id retains its existing wire shape. Expiry exposes failed,
`stale_running` and finishedAt; the active task is stopped by existing settlement.
No score/verdict publication is introduced. Running judge/recheck UI explains
that requirement counts update when a batch finishes; terminal UI does not animate.
