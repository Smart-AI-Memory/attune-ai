---
type: faq
name: local-telemetry-trackers-need-an-autouse-conftest-fixture
tags: [testing, imports, git, claude-code]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about local-telemetry trackers need an autouse conftest fixture disabling them, not just a tmp_path default?

## Answer

a new `HelpTracker` class with the default path `~/.attune/telemetry/` got exercised through its real consumer (MCP handler `_handle_help_lookup`) during routine tests and polluted the user's actual JSONL with 11 test-fixture events. `tmp_path` only helps when the test constructs the tracker directly; tests that reach the tracker via production code paths bypass the fixture.

```
HelpTracker
```

## Related Topics
- **Error**: Detailed error: Local-telemetry trackers need an autouse
  conftest fixture disabling them, not just a
  `tmp_path` default
