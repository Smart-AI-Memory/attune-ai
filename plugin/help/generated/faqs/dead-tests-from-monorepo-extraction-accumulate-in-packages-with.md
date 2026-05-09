---
type: faq
name: dead-tests-from-monorepo-extraction-accumulate-in-packages-with
tags: [ci, testing, security, git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about dead tests from monorepo extraction accumulate in packages with no CI?

## Answer

attune-help shipped `test_plugin_config.py` (15 tests) and parts of `test_plugin_references.py` from attune-ai's monorepo split. They validated a `plugin/` directory layout that exists in attune-ai but was never created in attune-help.

```
test_plugin_config.py
```

## Related Topics
- **Error**: Detailed error: Dead tests from monorepo extraction accumulate
  in packages with no CI
