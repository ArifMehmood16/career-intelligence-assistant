# Feature Specification: PolyForm noncommercial reuse

**Branch**: `docs/phase-19-noncommercial-license`
**Created**: 2026-10-08
**Status**: Unchanged PolyForm adopted and locally verified
**Input**: Human selected unchanged PolyForm Noncommercial after reviewing its
standard organisational exceptions, with copyright retained and an option to
negotiate commercial revenue. This supersedes the custom draft in f1d1f4e.

Root: [Licensing policy](../../PLAN.md#licensing-policy--2026-10-08) and
[BACKLOG](../../BACKLOG.md#now--prove-the-current-product). Legal-text/documentation
scope only; not professional legal advice or an application architecture change.

## User Scenarios & Testing

### US1 — Learn, share and collaborate (P1)

A user studies, runs, forks, modifies and shares the code under PolyForm's permitted
purposes and notice requirements. Independent check: unchanged official licence
text, required owner notice and matching current summaries.
Acceptance: standard personal/noncommercial and listed organisational permissions
remain intact; no custom extra restrictions or silent removal of the patent grant.

### US2 — Retain ownership and negotiate commercial permission (P1)

The owner keeps copyright in their original code, including copied portions in
modified versions, and can negotiate a separate commercial licence for rights
they control. Independent review: distinguish copyright ownership from permission
to use and from a contractual right to licence fees or a revenue share.
Acceptance: no promise of ownership of others' original additions, automatic
royalties, all revenue, or payment from uses PolyForm already permits.

### US3 — Contribute with clear rights (P2)

Contributors retain their copyright and submit under the same PolyForm terms.
Independent review: no assignment or separate commercial licence is implied by
contributing; commercial licensing must secure required contributor permissions.
Acceptance: third-party licences remain unchanged and outside this project licence.

## Requirements

- **FR-001**: Use unchanged official PolyForm Noncommercial 1.0.0 in LICENSE,
  including its standard permitted purposes, notices, patent and violation terms.
- **FR-002**: Preserve Arif Mehmood's original copyright through a separate
  Required Notice; explain that modified copies do not transfer ownership of
  original code, and original additions remain their authors' property.
- **FR-003**: Explain separate commercial permission outside existing grants,
  optional negotiated fees/revenue share, and the absence of automatic royalties
  or ownership of someone else's entire derivative project.
- **FR-004**: Preserve third-party licences, contributor ownership and lawful
  independent implementations; add no extra restrictions to PolyForm.
- **FR-005**: Align README, contribution/licensing guidance and root acceptance;
  describe the standard organisational exceptions and source-available status.
- **FR-006**: Change no runtime code, dependencies, lockfiles, settings or private
  data. Record observed checks and deliver on the existing PR #49 branch.

## Success Criteria

- **SC-001**: LICENSE is byte-identical to the official plain-text download;
  ownership/revenue summaries agree with its actual permissions and separate terms.
- **SC-002**: Existing third-party licence/notice files remain byte-for-byte intact.
- **SC-003**: Documentation links and branch whitespace pass; intended licensing
  files only are committed and the unrelated npm lock change is preserved.

## Edge cases and assumptions

Listed charitable, educational, public research, public safety/health,
environmental and government organisations retain PolyForm's funding-independent
permissions. No blanket nonprofit commercial prohibition is added. Standard
noncommercial wording does not enumerate every favor or indirect gain. Revenue
sharing needs a separate agreement with a licensee, and cannot be imposed on a
use already permitted by PolyForm. Contributor/third-party rights remain separate.
Copyright exceptions and independent work are not turned into royalty obligations.
