---
type: error
name: github-copilot-autofix-pushes-commits-directly-to-pr-branches
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Error: GitHub Copilot Autofix pushes commits
  directly to PR branches when CodeQL finds
  fixable issues — expect a rebase mid-session

## Signature

GitHub Copilot Autofix pushes commits
  directly to PR branches when CodeQL finds
  fixable issues — expect a rebase mid-session

## Root Cause

during PR #169 remediation, a commit `65321257 Potential fix for pull request finding 'Empty except'` appeared on `origin/feat/help-system-maintenance-2026-04-19` with no action from me. Author was my own account but co-authored-by "Copilot Autofix powered by AI <...@github-code-quality[bot]...>". The change was a one-line explanatory comment on an empty `except: pass` block — cosmetic, not logic. My next `git push` rejected with "non-fast-forward"; fixed by `git pull --rebase` then `git commit --amend -S --no-edit` (rebase replays commits unsigned, per the existing lesson) then re-push. Behaviors to expect: (a) these commits land silently whenever CodeQL emits a fixable finding the autofix engine has a template for; (b) they're usually comment additions or trivial guards, not logic changes; (c) they can land between your local push and any subsequent work, so always `git fetch` + inspect before assuming a push failure is a race with a human collaborator. Autofix commits are safe to keep — review the diff, confirm it's cosmetic, rebase on top.

## Resolution

1. during PR #169 remediation, a commit `65321257 Potential fix for pull request finding 'Empty except'` appeared on `origin/feat/help-system-maintenance-2026-04-19` with no action from me

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Warning: Avoid: GitHub Copilot Autofix pushes commits
  directly to PR branches when CodeQL finds
  fixable issues — expect a rebase mid-session
- Tip: Best practice: GitHub Copilot Autofix pushes commits
  directly to PR branches when CodeQL finds
  fixable issues — expect a rebase mid-session
