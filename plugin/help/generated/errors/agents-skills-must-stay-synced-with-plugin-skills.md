---
type: error
name: agents-skills-must-stay-synced-with-plugin-skills
confidence: Verified
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# Error: `.agents/skills/` must stay synced with `plugin/skills/`

## Signature

`.agents/skills/` must stay synced with `plugin/skills/`

## Root Cause

Adding a new skill directory under `plugin/skills/` without also creating a matching `.agents/skills/<name>/SKILL.md` fails the `test_all_plugin_skills_synced` test. Run `python scripts/sync_agents_skills.py --write` after adding or modifying skills, or the `test_skill_body_content_matches` test will also fail.

## Resolution

1. Adding a new skill directory under `plugin/skills/` without also creating a matching `.agents/skills/<name>/SKILL.md` fails the `test_all_plugin_skills_synced` test
2. Run `python scripts/sync_agents_skills.py --write` after adding or modifying skills, or the `test_skill_body_content_matches` test will also fail

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Task: Update test mocks and assertions
