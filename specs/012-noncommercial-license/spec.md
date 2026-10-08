# Feature Specification: Noncommercial reuse and collaboration

**Branch**: `docs/phase-19-noncommercial-license`
**Created**: 2026-10-08
**Status**: Implemented and locally reviewed
**Input**: Human requests free learning, use, duplication, modification and
collaboration; commercial gain from original or modified code requires permission.

Human-authorized scope: [Licensing policy](../../PLAN.md#licensing-policy--2026-10-08)
and [BACKLOG](../../BACKLOG.md#now--prove-the-current-product). This is a legal-text
and documentation change, not a new application phase or a claim of legal review.

## User Scenarios & Testing

### US1 — Learn, share and collaborate (P1)

A learner runs the project, forks it, modifies it and shares it freely for
noncommercial purposes while preserving credit and the licence.
Independent review: each action is expressly permitted, including free hosting.
Acceptance: noncommercial personal, educational, research and nonprofit activity
is permitted; a modified copy retains the commercial restriction and attribution.

### US2 — Request commercial permission (P1)

Someone wants to sell a fork, run a paid service, use it in a business, or receive
money or valuable commercial favors in exchange for its use or related services.
Independent review: each requires Arif Mehmood's prior explicit written permission,
including indirect benefits, modified copies and free business use.
Acceptance: nonprofit status or lack of profit does not excuse a commercial use;
ordinary learning, collaboration and credit are not prohibited benefits.

### US3 — Contribute without claiming other people's rights (P2)

A contributor reads the contribution terms and retains copyright in their work.
Independent review: contributions use the same noncommercial terms; there is no
silent assignment or automatic commercial licence. Third-party licences survive.
Acceptance: general ideas and independent implementations are not claimed as
copyrighted code; third-party materials keep their existing terms.

## Requirements

- **FR-001**: Expressly permit noncommercial use, study, copying, forking,
  modification, distribution, hosting and collaboration with attribution.
- **FR-002**: Require prior explicit written owner permission for direct/indirect
  commercial advantage, revenue, profit, payment, barter or valuable commercial
  favors, including internal business use and paid services without distribution.
- **FR-003**: Apply restrictions to covered portions of modified, renamed,
  translated, combined and derivative copies; no commercial relicensing loophole.
- **FR-004**: Preserve third-party licences, contributor ownership, statutory
  exceptions and valid pre-existing permissions; do not claim ownership of ideas.
- **FR-005**: Align README and contribution guidance with the full licence;
  retain warranty/liability protection and state source-available status.
- **FR-006**: Change no runtime code, dependencies, lockfiles, private settings or
  user documents; record observed checks and keep branch/commit scope reviewable.

## Success Criteria

- **SC-001**: All allowed and restricted actions in US1/US2 have express terms in
  the licence and no conflicting current README description.
- **SC-002**: Third-party licence files remain byte-for-byte unchanged.
- **SC-003**: Local documentation links resolve and branch whitespace checks pass;
  the commit contains only licensing and its linked change records.

## Edge cases and assumptions

Commercial purpose controls, not the organisation's nonprofit registration or
whether a fee exceeds costs. Ordinary knowledge and contributor credit are allowed;
commercial quid-pro-quo favors are restricted. General-purpose infrastructure or
model costs alone do not commercialise an otherwise permitted use; selling or
providing paid Software-based services still requires permission. Independently written work merely
inspired by an idea is outside these copyright terms. Arif Mehmood is the existing
named copyright owner; permissions cover only rights the grantor controls.
