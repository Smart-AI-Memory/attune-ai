---
type: warning
name: dispatch-tables-hold-direct-function-references-mocks-must
confidence: Verified
tags: [testing, imports]
source: .claude/CLAUDE.md
---

# Warning: Dispatch tables hold direct function references — mocks
  must target the table, not the module name

## Condition

When `_SUBCOMMAND_DISPATCH` or `_SIMPLE_DISPATCH` in `cli_minimal.py` captures `cmd_foo` at import time, `@patch("attune.cli_minimal.cmd_foo")` replaces the module attribute but the dispatch table still calls the original

## Risk

This caused 20+ pre-existing test failures

## Mitigation

1. use `patch.dict("attune.cli_minimal._SUBCOMMAND_DISPATCH", {command: {**orig, subcommand: mock_fn}})` to replace the entry in the dispatch table itself

## Confidence

**Verified** — Confirmed by prior incident (Lessons Learned)

## Related Topics
- Error: Diagnostic help: Dispatch tables hold direct function references — mocks
  must target the table, not the module name
