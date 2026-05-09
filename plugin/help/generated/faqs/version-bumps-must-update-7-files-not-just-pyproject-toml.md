---
type: faq
name: version-bumps-must-update-7-files-not-just-pyproject-toml
tags: [testing, git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about version bumps must update 7+ files, not just pyproject.toml?

## Answer

The version lives in `pyproject.toml`, `plugin/.claude-plugin/ plugin.json`, `plugin/.claude-plugin/marketplace.json` (two fields: `metadata.version` and `plugins[0].version`), `plugin/core/ __init__.py`, `.claude-plugin/marketplace.json` (root-level), `.claude/CLAUDE.md` (header and footer), AND `docs/reference/API_REFERENCE.md` (header). The test `test_all_versions_match` in `test_plugin_config_validation.py` catches the plugin-config mismatches but NOT the API_REFERENCE drift — that one has to be caught by hand.

```
pyproject.toml
```

## Related Topics
- **Error**: Detailed error: Version bumps must update 7+ files, not just `pyproject.toml`
