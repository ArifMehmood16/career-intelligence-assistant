# Gap contract

GET /api/roles/{id}/verdicts gapPlan dimension accepts exactly match, seniority,
experience, recency. Current recency 0.6 renders Evidence recency · current weight
60%; match/experience/seniority retain now X / 4. Delta stays server-computed and
ordered; the frontend does not rescore. Unknown dimensions remain invalid.
