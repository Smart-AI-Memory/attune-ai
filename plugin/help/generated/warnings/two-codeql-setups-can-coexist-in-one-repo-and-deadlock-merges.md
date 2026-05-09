---
type: warning
name: two-codeql-setups-can-coexist-in-one-repo-and-deadlock-merges
confidence: Verified
tags: [testing, git, python]
source: .claude/CLAUDE.md
---

# Warning: Two CodeQL setups can coexist in one repo and
  deadlock merges silently

## Condition

`attune-ai` had BOTH `.github/workflows/codeql.yml` (custom, with `pull_request:` trigger) AND GitHub's default CodeQL setup (`"schedule":"weekly"`, no PR trigger)

## Risk

Result: PR #173 sat with 24 passing checks + `Analyze (python)` silently absent from the rollup, and admin-merge couldn't bypass because the gate was declared "expected" but missing

## Mitigation

1. `attune-ai` had BOTH `.github/workflows/codeql.yml` (custom, with `pull_request:` trigger) AND GitHub's default CodeQL setup (`"schedule":"weekly"`, no PR trigger)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Two CodeQL setups can coexist in one repo and
  deadlock merges silently
