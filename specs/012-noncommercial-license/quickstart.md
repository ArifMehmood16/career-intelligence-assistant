# Licensing validation guide

Review the eight human-provided scenarios against LICENSE: personal learning,
internal business tools, closed-source modifications and free unmonetised public
products are allowed; selling containing products, subscriptions/paid services,
ads/sponsorship and removal of original credit are not allowed by the public grant.
External monetisation needs prior written permission, including for modified code.

Check paid internal worker administration versus paid tool-based client services,
retained copyright versus ownership of contributors' additions, negotiated fees
versus automatic revenue claims, and preservation of valid earlier licence grants.
Check attribution locations in NOTICE/README/CONTRIBUTING/docs/licensing.md; confirm
there is no source-publication or per-output credit requirement. Current summaries
must call this custom source-available licensing, not unchanged PolyForm.

Check local Markdown links and git diff --check. Compare existing third-party
notices with origin/main byte-for-byte. Inspect staged paths; do not stage/reset
frontend/package-lock.json or alter runtime code/settings/dependencies.
No text-matching test proves legal enforceability. Existing PR CI runs ordinary
regressions without paid provider calls. Update PR #49 without merging.
