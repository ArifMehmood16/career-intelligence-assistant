# PolyForm validation guide

Compare LICENSE byte-for-byte with the official plain-text download:
https://polyformproject.org/licenses/noncommercial/1.0.0.txt
Check NOTICE has Arif's Required Notice and that README/CONTRIBUTING link it.
Read docs/licensing.md against actual organisational/personal permissions, patent
terms and No Other Rights. No fee/revenue clause may be inserted into LICENSE.

Review ownership of original code versus contributors' additions, negotiated fees
versus automatic revenue claims, and preserve standard organisational exceptions.
Check local documentation links and git diff --check; compare existing third-party
notices with origin/main byte-for-byte. Inspect staged paths; do not stage/reset
frontend/package-lock.json or alter runtime code/settings/dependencies.

No text-matching test proves legal enforceability. Existing PR CI runs ordinary
regressions without paid provider calls. Push/update PR #49 without merging.
