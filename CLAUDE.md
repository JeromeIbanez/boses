# Claude Code Instructions

## Branch Workflow — STRICTLY ENFORCED

- **All code changes go to `staging` first.** Always `git checkout staging` before making any changes.
- **Push to `origin/staging` automatically** after every commit — no need to ask Jerome.
- **Never push to `main` unless Jerome explicitly approves.** Approval phrases: "do it", "push to prod", "push to production", "looks good", "ship it", or equivalent.
- When Jerome approves: `git checkout main && git merge staging && git push origin main`, then sync back: `git checkout staging && git merge main && git push origin staging`.

**`main` = production. Do not touch it until told to.**
