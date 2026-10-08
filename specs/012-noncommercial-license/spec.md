# Feature Specification: Internal use and external monetisation permission

**Branch**: `docs/phase-19-noncommercial-license`
**Created**: 2026-10-08
**Status**: Revised custom policy implemented and locally verified; PR CI required
**Input**: Human permits internal business use, closed-source modifications and
free unmonetised public products. External monetisation requires separate written
permission. Preserve Arif Mehmood's copyright and visible attribution. This latest
policy supersedes the initial strict custom draft and the PolyForm continuation.

Root: [Licensing policy](../../PLAN.md#licensing-policy--2026-10-08) and
[BACKLOG](../../BACKLOG.md#now--prove-the-current-product). Legal-text/documentation
scope only; no application architecture change or professional legal review.

## User Scenarios & Testing

### US1 — Learn, build and use internally (P1)

A person or organisation runs, copies, forks and modifies the software for learning
or internal operations, including in a profitable company. They may keep changes
closed-source. A free public product is permitted if it is not monetised.
Acceptance: express permissions cover these uses; retaining attribution does not
require publishing source. Internal productivity, cost savings and ordinary
business profits do not require a separate licence.

### US2 — Reserve external monetisation and retain ownership (P1)

Selling software containing covered code, subscriptions, paid hosted/API services,
paid tool-based client analysis, and advertising/sponsorship of an otherwise free
product require prior written permission. Modification or renaming does not avoid
this boundary. Ordinary internal administration by a paid worker is allowed.
Acceptance: commercial permission may negotiate fees/revenue share, but creates
no automatic entitlement to another person's revenue or original additions.

### US3 — Share with credit and contribute with clear rights (P2)

Copies retain LICENSE/NOTICE and original copyright. Externally distributed or
hosted user-facing products show Arif Mehmood's name and project/licence links in
an accessible About, Credits or Legal location; accompanying public documentation
also retains credit. Contributors keep their copyright and offer their changes
under the same terms, without an assignment or additional monetisation grant.
Acceptance: third-party terms, independent work, statutory exceptions and valid
prior licence grants remain intact. No source publication or per-output credit.

## Requirements

- **FR-001**: Write a clearly named custom source-available licence, allowing
  personal/learning use, internal business use regardless of profitability,
  closed-source modifications and free unmonetised external products/services.
- **FR-002**: Define external monetisation and require prior written permission
  for sales, subscriptions, paid services and advertising/sponsorship-supported
  products, including modified versions. Distinguish internal business benefits.
- **FR-003**: Preserve original copyright and require retained notices plus
  accessible external product/documentation attribution to Arif Mehmood.
- **FR-004**: Preserve contributor/third-party rights, independent ideas and work,
  statutory exceptions, valid earlier grants and warranty/liability boundaries.
  Claim no automatic ownership, royalty, revenue share or assignment.
- **FR-005**: Align README, NOTICE, contribution/licensing guidance and root
  acceptance with this policy; identify it as custom, not unchanged PolyForm.
- **FR-006**: Change no runtime code, dependencies, lockfiles, settings or private
  data. Record observed checks and deliver on existing PR #49 without merging.

## Success Criteria

- **SC-001**: Review all eight human-provided use cases against explicit licence
  clauses; current summaries agree on permissions, attribution and revenue limits.
- **SC-002**: Existing third-party licence/notice files remain byte-for-byte intact.
- **SC-003**: Documentation links and branch whitespace pass; only intended files
  are committed and the unrelated npm lock working copy is preserved.

## Edge cases and assumptions

Paid staff/contractors may operate an organisation's private internal tools on its
behalf. Charging external clients for the tool's analysis/functionality is a paid
service requiring permission; ordinary internal administration does not become
restricted merely because the organisation sells unrelated goods or services.
The licence governs covered software, not ownership of user inputs or outputs.
Earlier valid grants cannot be retroactively revoked by this policy revision.
Additional external monetisation rights require the necessary rights holders'
permission; no royalty rate or future commercial agreement is invented here.
