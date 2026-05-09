---
type: error
name: version-bumps-must-update-7-files-not-just-pyproject-toml
confidence: Verified
tags: [testing, git, claude-code]
source: .claude/CLAUDE.md
---

# Error: Version bumps must update 7+ files, not just `pyproject.toml`

## Signature

Version bumps must update 7+ files, not just `pyproject.toml`

## Root Cause

The version lives in `pyproject.toml`, `plugin/.claude-plugin/ plugin.json`, `plugin/.claude-plugin/marketplace.json` (two fields: `metadata.version` and `plugins[0].version`), `plugin/core/ __init__.py`, `.claude-plugin/marketplace.json` (root-level), `.claude/CLAUDE.md` (header and footer), AND `docs/reference/API_REFERENCE.md` (header). The test `test_all_versions_match` in `test_plugin_config_validation.py` catches the plugin-config mismatches but NOT the API_REFERENCE drift — that one has to be caught by hand. As of v6.3.0, API_REFERENCE had silently lagged 2 minor versions (stayed at 5.3.2 through v6.0, v6.1, v6.2, v6.3). Grep for the old version string across the whole repo before committing a bump, and include `docs/reference/API_REFERENCE.md` in every release-prep checklist.

## Resolution

1. Grep for the old version string across the whole repo before committing a bump, and include `docs/reference/API_REFERENCE.md` in every release-prep checklist

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
