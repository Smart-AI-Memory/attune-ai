---
type: warning
name: adding-a-plugin-skill-has-three-enforcement-gates-not-one
confidence: Verified
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# Warning: Adding a plugin skill has THREE enforcement gates,
  not one

## Condition

Besides creating `plugin/skills/<name>/SKILL.md`, you must also (1) bump the hardcoded count in `tests/unit/plugins/test_plugin_config_validation.py:: TestPluginStructure::test_skill_count`, (2) add a row to the "Skills Reference" table in `plugin/skills/attune-hub/SKILL.md` (enforced by `tests/unit/plugins/test_plugin_reference_validation.py:: TestCoverage::test_all_skill_dirs_referenced_by_attune_hub`), and (3) run `python scripts/sync_agents_skills.py` to regenerate the `.agents/skills/` mirror (enforced by `test_skill_body_content_matches`)

## Risk

Missing any one fails CI

## Mitigation

1. Besides creating `plugin/skills/<name>/SKILL.md`, you must also (1) bump the hardcoded count in `tests/unit/plugins/test_plugin_config_validation.py:: TestPluginStructure::test_skill_count`, (2) add a row to the "Skills Reference" table in `plugin/skills/attune-hub/SKILL.md` (enforced by `tests/unit/plugins/test_plugin_reference_validation.py:: TestCoverage::test_all_skill_dirs_referenced_by_attune_hub`), and (3) run `python scripts/sync_agents_skills.py` to regenerate the `.agents/skills/` mirror (enforced by `test_skill_body_content_matches`)

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Adding a plugin skill has THREE enforcement gates,
  not one
