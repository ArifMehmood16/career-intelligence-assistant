# Existing retirement and publication contract

No new public endpoint or response field.

- Upgrade b2d9c8e4f601 → c4e8a1d7b902 deletes non-v2 scores and their same-version drafts, marks unsupported ready roles failed, drops retired tables/workspace selector and retains current storage.
- `/api/roles/{id}`, `/verdicts`, `/requirements`, `/breakdown`, `/gap-plan` and `/api/ranking` derive fit and evidence from the same current publication. The role summary rounds the persisted fit; detailed verdict output retains precision.
- Interview pack, bullet and cover-letter routes use validated chunk projections. Citations resolve via `/api/spans/{id}` to stored source text; generated artifacts never feed fit.
- `/api/messages` fit/gap answers and MCP list_roles/gap tools use current role-analysis views. Invalidated/no-current results cannot receive a ranking or grounded generation.
- Hard deletion removes originals and all derived records in one workspace without affecting another.
