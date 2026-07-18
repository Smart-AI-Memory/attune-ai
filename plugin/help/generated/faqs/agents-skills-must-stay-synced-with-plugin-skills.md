---
type: faq
name: agents-skills-must-stay-synced-with-plugin-skills
tags: [testing, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about .agents/skills/ must stay synced with plugin/skills/?

## Answer

Adding a new skill directory under `plugin/skills/` without also creating a matching `.agents/skills/<name>/SKILL.md` fails the `test_all_plugin_skills_synced` test.

**How to fix:**
- Run `python scripts/sync_agents_skills.py --write` after adding or modifying skills, or the `test_skill_body_content_matches` test will also fail

```
plugin/skills/
```

## Related Topics
- **Error**: Detailed error: `.agents/skills/` must stay synced with `plugin/skills/`
