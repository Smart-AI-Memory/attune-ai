---
name: commit-push-pr
description: Stage, commit, push, and create PR in one command
---
# commit-push-pr

One-shot command to commit current work, push, and open a PR.

## Context (pre-computed)

```bash
git status -u
git diff --stat
git log --oneline -5
git branch --show-current
```

## Instructions

1. Review the git status and diff above
2. Stage all relevant changed files (exclude .env,
   credentials, large binaries)
3. Write a conventional commit message based on the
   changes:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `chore:` for maintenance
   - `refactor:` for restructuring
4. Commit with the message
5. Push the current branch to origin (create remote
   branch if needed with `-u`)
6. Create a PR targeting main using `gh pr create`
   with a summary and test plan
7. Return the PR URL

If on `main`, create a feature branch first based on
the change type (e.g., `feat/description` or
`fix/description`).
