# Feature Specification: Open-source reuse with creator attribution

**Branch**: `docs/phase-19-noncommercial-license`
**Created**: 2026-10-08
**Status**: Apache 2.0 implemented and locally verified; updated-head CI required
**Input**: Human chose open source to encourage contribution, with recognition that
Arif Mehmood started/created this project. This supersedes earlier noncommercial
and custom source-available policies on the same unmerged PR.

Root: [Licensing policy](../../PLAN.md#licensing-policy--2026-10-08) and
[BACKLOG](../../BACKLOG.md#now--prove-the-current-product). Licensing/documentation
scope only; no application architecture change or professional legal review.

## User Scenarios & Testing

### US1 — Use and contribute without a commercial permission gate (P1)

People and businesses may learn, run, fork, modify, distribute and monetise the
software under unchanged Apache License 2.0. Modifications may remain closed-source
subject to its terms. Independent check: official licence bytes and matching
current summaries, including patent grant and contribution provisions.
Acceptance: no custom noncommercial clause, royalty or permission requirement.

### US2 — Recognise the creator and preserve attribution (P1)

README and NOTICE identify Arif Mehmood as the project's original creator. Relevant
copyright and NOTICE attribution are retained when redistributing as required by
Apache section 4. Independent check: name, project link and accurate description
of standard notice placement choices.
Acceptance: no mandatory About screen, credit on every output, endorsement, or
claim to exclusive ownership of the general idea or contributors' original work.

### US3 — Contribute under the same recognised terms (P2)

Intentionally submitted contributions use Apache 2.0 unless explicitly stated
otherwise, consistent with section 5. Contributors keep copyright; no assignment
or extra CLA is introduced. Third-party materials retain their own terms.
Acceptance: licence guidance accurately describes copyright and patent grants,
commercial permission, third-party scope and valid earlier grants.

## Requirements

- **FR-001**: Replace custom LICENSE with unchanged official Apache License 2.0;
  allow commercial/paid/closed-source reuse under its standard conditions.
- **FR-002**: Credit Arif Mehmood as original project creator in README and NOTICE;
  preserve relevant copyright and attribution through standard section 4 terms.
- **FR-003**: Align contribution guidance with Apache section 5, retained contributor
  copyright and standard grants, without extra paperwork or owner-only rights.
- **FR-004**: Preserve third-party terms, statutory exceptions and valid earlier
  grants. Claim no exclusive ownership of ideas, automatic royalties or endorsement.
- **FR-005**: Align current licensing guidance, PLAN/BACKLOG and bounded spec records;
  retain earlier policy checkpoints as history, not current restrictions.
- **FR-006**: Change no runtime code, dependencies, lockfiles, settings or private
  data. Record observed checks; deliver through existing PR #49 without merging.

## Success Criteria

- **SC-001**: LICENSE matches official Apache 2.0 bytes; current summaries agree
  with commercial/closed-source permissions, notice placement and standard grants.
- **SC-002**: All four existing third-party licence/notice files remain unchanged.
- **SC-003**: Local links and branch whitespace pass; only intended files are
  committed, preserving the unrelated npm lock working copy. Observe new-head CI.

## Edge cases and assumptions

Creator credit documents the origin of this project, not a claim that nobody else
has independently conceived a similar idea. Apache 2.0 preserves relevant legal
notices on redistribution but does not require credit in every product UI or
hosted output. No additional attribution condition is added. Contributor copyright
stays with its holder; standard copyright/patent grants still apply. Earlier valid
licence grants continue on their own terms for versions offered under them.
