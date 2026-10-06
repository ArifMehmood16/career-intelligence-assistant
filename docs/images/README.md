# Screenshot provenance

Refreshed 2026-10-06 on `test/phase-19-retirement-verification` for PR #47 using the
in-app Browser at `http://localhost:3000/dev/states`. Images are JPEG captures of
actual rendered components with synthetic props from
`frontend/src/routes/dev.states.tsx`. No personal workspace, CV/job contents,
credentials or live provider responses were captured. Each section is a separate
example; scores and timings are fixtures, not evaluation measurements.

- `workspace.jpg`: populated synthetic roles table with fit and requirement counts.
- `settings.jpg`: answer/index provider choices and unavailable-reason examples.
- `analysis-progress.jpg`: fixed-clock seven-task judging progress and call estimate.
- `fit.jpg`: Fit, keyword coverage, evidence and all three requirement statuses.
- `fit-filters.jpg`: Missing plus 0–24% selection, showing one of three cards.
- `gaps.jpg`: potential fit-score gains, including evidence recency.
- `prepare.jpg`: interview probes, cited evidence, thin areas and questions.
- `letter.jpg`: generated paragraph, resolved source glossary, export and versions.
- `ask.jpg`: completed answer, source citation chips and provider attribution.

The gallery provider dialog and evidence drawer were dismissed before capture.
Images use the browser's 1280-pixel viewport width and each section's full height,
so labels and source passages remain complete. The filter was selected through
its rendered control. All nine images were visually inspected after capture.
The Letter gallery now supplies its existing synthetic evidence as a resolved
citation prop; it performs no network lookup or generation. The completed Ask
fixture confines its sticky composer to its own scroll frame, matching a standalone
chat layout rather than the gallery page viewport.

These document this PR's components. The separate open PR #46's fit-contribution
arrows, contextual experience changes and Ask loading changes are not depicted
as shipped on this branch. There is no claim of a full backend browser journey.
