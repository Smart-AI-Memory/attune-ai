---
type: faq
name: dispatch-tables-hold-direct-function-references-mocks-must
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# FAQ: What do I need to know about dispatch tables hold direct function references — mocks must target the table, not the module name?

## Answer

When `_SUBCOMMAND_DISPATCH` or `_SIMPLE_DISPATCH` in `cli_minimal.py` captures `cmd_foo` at import time, `@patch("attune.cli_minimal.cmd_foo")` replaces the module attribute but the dispatch table still calls the original. This caused 20+ pre-existing test failures.

**How to fix:**
- use `patch.dict("attune.cli_minimal._SUBCOMMAND_DISPATCH", {command: {**orig, subcommand: mock_fn}})` to replace the entry in the dispatch table itself

```
_SUBCOMMAND_DISPATCH
```

## Related Topics
- **Error**: Detailed error: Dispatch tables hold direct function references — mocks
  must target the table, not the module name
