# Additive contracts
GET /roles/{id}/verdicts: per verdict optional scoreImpact (earned, possible,
shortfall) or null; experienceExpected, yearsExpected, seniorityExpected. Values
come from validated stored publication; old missing metadata returns null.
Existing fields/status codes unchanged. Filters preserve point attribution.
Qualitative experience extraction is optional; server retains only verbatim
requirement phrases. Existing judge output uses the same 0–4 dimension shape with
qualitative anchors when years absent. Whole context is untrusted and budgeted.
Ask status is visible/accessible immediately with Stop available; final outcomes
clear status. No SSE or provider API change.
