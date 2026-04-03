---
type: warning
name: github-repos-serve-as-claude-code-marketplaces
confidence: Verified
tags: [git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: GitHub repos serve as Claude Code marketplaces

## Condition

Add `.claude-plugin/marketplace.json` at the repo root with a `source` field pointing to the plugin subdirectory (e.g., `"./plugin"`)

## Risk

Ignoring this guidance may cause: GitHub repos serve as Claude Code marketplaces

## Mitigation

1. Add `.claude-plugin/marketplace.json` at the repo root with a `source` field pointing to the plugin subdirectory (e.g., `"./plugin"`)
2. Users install with two commands: `claude plugin marketplace add Smart-AI-Memory/attune-ai` then `claude plugin install attune-ai@attune-ai`

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: GitHub repos serve as Claude Code marketplaces
