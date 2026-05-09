---
type: warning
name: git-pull-refuses-with-unstaged-changes-when-pull-rebase-true
confidence: Verified
tags: [git]
source: .claude/CLAUDE.md
---

# Warning: `git pull` refuses with unstaged changes when
  `pull.rebase=true`

## Condition

This repo's git config sets `pull.rebase=true`, so `git pull` invokes rebase, which fails immediately if the working tree has any unstaged changes — even if those changes don't conflict with the incoming commits

## Risk

This repo's git config sets `pull.rebase=true`, so `git pull` invokes rebase, which fails immediately if the working tree has any unstaged changes — even if those changes don't conflict with the incoming commits

## Mitigation

1. Useful when local main is strictly behind origin/main and you have unrelated in-flight work

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: `git pull` refuses with unstaged changes when
  `pull.rebase=true`
