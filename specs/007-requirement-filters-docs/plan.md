# Implementation plan — requirements and documentation

Existing TypeScript/React, Bun/Vitest and native controls styled like ComparePanel;
no stack changes. Scope and acceptance: spec.md, root PLAN/BACKLOG 19.1.

## Existing modules and design

Extract the ready requirements section from VerdictsPanel into RequirementsPanel.
Local filter state uses existing verdict label and requirementScore only. Render
stored score as a whole percentage, with four inclusive ranges over that displayed
percentage and an explicit Not scored option; null is never coerced to zero.
Use labelled native selects and existing buttons/tokens. Combined filters retain
ordering, evidence and trace callbacks; a publication-keyed child resets filters.
Initial filter props permit synthetic gallery filtered/empty states. Fit summary
and keyword coverage remain outside the filtered list.

Update README and docs/architecture.md Mermaid diagrams from inspected application
and adapter source, not historical v1 assumptions. Refresh existing screenshot
assets from current synthetic component gallery and document capture provenance.
No personal app/API data enters screenshots. Keep stale release gates visibly open.

## Constitution checks before and after design

Pass: same validated publication and domain scoring, no model/provider work or API
change; bounded system diagram preserves SQL/cancellation/egress boundaries. No new
dependency or migrations. One current branch by explicit human direction, with green
commits. Existing privacy and test gates maintained. All requirements mapped to tasks.

## Validation

Focused red/green component interactions: combined filters, zero/unscored, empty
selection, clear, new publication and preserved overall fit/trace action. Gallery
mount tests, frontend lint/typecheck, full make lint/test, browser interaction and
synthetic screenshot inspection. Earlier 141 SQL tests remain evidence for unchanged
backend; rerun only if new persistence work requires it.
