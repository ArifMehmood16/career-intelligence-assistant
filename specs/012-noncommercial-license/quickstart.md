# Licensing validation guide

Review LICENSE sections against spec.md's allowed and restricted actions. Confirm
README links the authoritative licence and CONTRIBUTING explains incoming terms.
Inspect commercial restrictions for modified/forked copies, internal business use,
free commercial services, nonprofit commercial activity and payment in kind.
Confirm ordinary learning, credit and noncommercial collaboration remain allowed.

Run git diff --check, verify local Markdown links, and compare upstream font/Spec Kit
licence files with origin/main byte-for-byte. Inspect the full staged diff and file
list: only licence/policy documentation and this bounded change record may be staged.
Do not stage or reset the unrelated frontend/package-lock.json working-tree change.

No runtime tests prove licence enforceability. Application code is unchanged;
existing PR CI may run normal regression checks without paid provider calls.
