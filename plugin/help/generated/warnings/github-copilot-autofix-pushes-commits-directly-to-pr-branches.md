---
type: warning
name: github-copilot-autofix-pushes-commits-directly-to-pr-branches
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: GitHub Copilot Autofix pushes commits
  directly to PR branches when CodeQL finds
  fixable issues — expect a rebase mid-session

## Condition

during PR #169 remediation, a commit `65321257 Potential fix for pull request finding 'Empty except'` appeared on `origin/feat/help-system-maintenance-2026-04-19` with no action from me

## Risk

The change was a one-line explanatory comment on an empty `except: pass` block — cosmetic, not logic

## Mitigation

1. during PR #169 remediation, a commit `65321257 Potential fix for pull request finding 'Empty except'` appeared on `origin/feat/help-system-maintenance-2026-04-19` with no action from me

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: GitHub Copilot Autofix pushes commits
  directly to PR branches when CodeQL finds
  fixable issues — expect a rebase mid-session
