---
type: warning
name: version-bumps-must-update-7-files-not-just-pyproject-toml
confidence: Verified
tags: [testing, git, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Version bumps must update 7+ files, not just `pyproject.toml`

## Condition

The version lives in `pyproject.toml`, `plugin/.claude-plugin/ plugin.json`, `plugin/.claude-plugin/marketplace.json` (two fields: `metadata.version` and `plugins[0].version`), `plugin/core/ __init__.py`, `.claude-plugin/marketplace.json` (root-level), `.claude/CLAUDE.md` (header and footer), AND `docs/reference/API_REFERENCE.md` (header)

## Risk

As of v6.3.0, API_REFERENCE had silently lagged 2 minor versions (stayed at 5.3.2 through v6.0, v6.1, v6.2, v6.3)

## Mitigation

1. The version lives in `pyproject.toml`, `plugin/.claude-plugin/ plugin.json`, `plugin/.claude-plugin/marketplace.json` (two fields: `metadata.version` and `plugins[0].version`), `plugin/core/ __init__.py`, `.claude-plugin/marketplace.json` (root-level), `.claude/CLAUDE.md` (header and footer), AND `docs/reference/API_REFERENCE.md` (header)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Version bumps must update 7+ files, not just `pyproject.toml`
