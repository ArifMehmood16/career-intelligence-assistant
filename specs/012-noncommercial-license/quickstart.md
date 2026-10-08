# Apache 2.0 validation guide

Compare LICENSE byte-for-byte with the official Apache License 2.0 plain text:
https://www.apache.org/licenses/LICENSE-2.0.txt
Check standard copyright/patent grants, redistribution terms and contribution
section remain unchanged. No commercial approval, royalty or extra UI-credit term.

Review current README/NOTICE/CONTRIBUTING/licensing guide: personal/internal use,
paid services, sales and closed-source modifications are allowed under Apache
terms. Preserve relevant copyright and NOTICE attribution with standard placement
options; identify changes as section 4 requires. Creator credit names Arif Mehmood
as this project's original creator without claiming exclusive rights in the idea.
Contributors retain copyright, submit under section 5 and give standard grants;
no assignment/CLA. Preserve valid earlier grants and third-party licences.

Check local Markdown file links and git diff --check. Compare the four existing
third-party notices against origin/main bytes and preserve the unrelated npm lock
working copy. Inspect the complete branch diff and stage only intended files.
No executable tests claim legal enforceability. Update existing PR #49, observe CI
on the pushed head and leave merging to the human.
