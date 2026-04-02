---
type: error
name: github-repos-serve-as-claude-code-marketplaces
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Error: GitHub repos serve as Claude Code marketplaces

## Signature

GitHub repos serve as Claude Code marketplaces

## Root Cause

Add `.claude-plugin/marketplace.json` at the repo root with a `source` field pointing to the plugin subdirectory (e.g., `"./plugin"`). Users install with two commands: `claude plugin marketplace add Smart-AI-Memory/attune-ai` then `claude plugin install attune-ai@attune-ai`. The marketplace clones from the default branch — changes must be merged to `main` before users see them.

## Resolution

1. Add `.claude-plugin/marketplace.json` at the repo root with a `source` field pointing to the plugin subdirectory (e.g., `"./plugin"`)
2. Users install with two commands: `claude plugin marketplace add Smart-AI-Memory/attune-ai` then `claude plugin install attune-ai@attune-ai`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Tip: Best practice: GitHub repos serve as Claude Code marketplaces
