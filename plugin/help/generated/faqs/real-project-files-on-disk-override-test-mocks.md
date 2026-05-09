---
type: faq
name: real-project-files-on-disk-override-test-mocks
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: What should I know about real project files on disk override test mocks?

## Answer

Tests that mock `_get_raw_suggestions()` at the definition site still get real suggestions from `_get_spec_suggestions()` which reads actual `.claude/plans/` files.

**How to fix:**
- mock at the *import site* in the consuming module (`attune.voice.formatter.get_next_steps` not `attune.voice.next_steps.get_next_steps`), or use `monkeypatch.chdir(tmp_path)` to isolate from the real filesystem

```
_get_raw_suggestions()
```

## Related Topics
- **Error**: Detailed error: Real project files on disk override test mocks
