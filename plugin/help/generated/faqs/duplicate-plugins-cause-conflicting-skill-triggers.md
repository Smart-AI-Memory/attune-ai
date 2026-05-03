---
name: duplicate-plugins-cause-conflicting-skill-triggers
source: .claude/CLAUDE.md
summary: This developer help template explains how installing both `attune-lite` and
  `attune-ai` plugins simultaneously creates duplicate skills that cause Claude to
  unpredictably select between conflicting versions, and recommends installing only
  one plugin at a time to prevent this issue.
tags:
- testing
- security
- claude-code
type: faq
---

# FAQ: What should I know about duplicate plugins causing conflicting skill triggers?

## Answer

Having both `attune-lite` and `attune-ai` installed creates duplicate skills (such as `security-audit`, `smart-test`, and others). When duplicates exist, Claude detects both versions and must arbitrarily select one, resulting in unpredictable behavior and a degraded user experience.

To avoid this issue, ensure that only one of the following plugins is installed at a time:

```
attune-lite
```

## Related Topics
- **Error**: Detailed error: Duplicate plugins cause conflicting skill triggers
