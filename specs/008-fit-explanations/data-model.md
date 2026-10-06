# Data model
PointImpact: earned, possible, shortfall floats in overall score points, all
nonnegative; earned + shortfall = possible. Missing attribution is null.
Qualitative experience_expected: optional verbatim requirement phrase, not years.
JudgeDocumentContext: immutable CV document ID/work text and JD ID/text; untrusted,
not new candidate evidence. Cache hashes content and includes all visible facts.
StoredVerdict expectations: optional experience phrase/years/level, JSON defaults
for older publications; unchanged match evidence and dimension rationale.
Ask: sending begins before network; remains true through stream and final history
fetch; stop/error/completion clear visible status. Cancellation cannot let an old
request reset a newer request's sending state.
